"""Career tools: job search, skill-gap analysis, resume analysis, roadmap generation.

These are the four capabilities exposed both to end users (via `app.py`'s
"Tools" tabs) and to external MCP clients (via `mcp_server.py`). Keeping the
logic here — rather than inline in either caller — mirrors the reasoning
behind `rag_service.py`: one implementation, multiple front doors, no risk of
behavior drifting between the Streamlit UI, the MCP server, and the LangSmith
evaluation harness in `evaluation.py`.

Three of the four tools (skill-gap analysis, resume analysis, roadmap
generation) ask the LLM for a JSON object matching a specific shape and parse
it with `_generate_json()`. The job-search tool is not an LLM call: it either
queries the Adzuna API (if `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` are configured)
or filters the small bundled dataset in `jobs_data.py`.

Every public function is wrapped with `@traceable` (see `tracing.py`) so runs
show up in LangSmith when tracing is enabled, and are no-ops otherwise.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from backend.config import Settings
from backend.errors import JobSearchError, LLMError
from backend.jobs_data import SAMPLE_JOBS
from backend.llm_providers import ChatMessage, LLMProvider
from backend.tracing import traceable

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Result types
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class JobListing:
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    skills: list[str] = field(default_factory=list)
    experience_level: str | None = None
    source: str = "bundled"


@dataclass(frozen=True)
class SkillGapResult:
    matched_skills: list[str]
    missing_skills: list[str]
    partially_met_skills: list[str]
    overall_readiness: str  # e.g. "low" | "medium" | "high"
    summary: str


@dataclass(frozen=True)
class ResumeAnalysis:
    extracted_skills: list[str]
    experience_summary: str
    strengths: list[str]
    gaps_or_improvements: list[str]
    suggested_target_roles: list[str]


@dataclass(frozen=True)
class RoadmapMilestone:
    title: str
    duration: str
    focus_skills: list[str]
    actions: list[str]


@dataclass(frozen=True)
class RoadmapResult:
    target_role: str
    milestones: list[RoadmapMilestone]
    summary: str


# --------------------------------------------------------------------------
# Shared LLM-JSON helper
# --------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of `text`, tolerating markdown code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = _JSON_BLOCK_RE.search(cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise LLMError("The model returned a response that wasn't valid JSON. Please try again.")


def _generate_json(llm: LLMProvider, prompt: str, *, system_instruction: str = "") -> dict:
    text = llm.generate(
        [ChatMessage(role="user", content=prompt)], system_instruction=system_instruction
    )
    return _extract_json(text)


def _as_str_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v).strip() for v in value if str(v).strip()]


# Domain profiles to validate skill-role compatibility
_DOMAIN_PROFILES = {

    # ============================================================
    # MEDICAL (clinical / non-engineering)
    # ============================================================
    "medical": {
        "role_keywords": {
            "nurse", "doctor", "physician", "surgeon", "medical", "clinical", "pharmacist",
            "radiologist", "therapist", "dentist", "health", "hospital", "patient", "nursing",
            "dentistry", "veterinary", "paramedic", "cardiology", "optometry", "physiotherapist",
            "midwife", "psychiatrist", "psychologist", "dietitian", "nutritionist", "anesthetist",
            "medical lab technician", "audiologist", "speech therapist", "occupational therapist",
        },
        "skill_keywords": {
            "ot", "opd", "operation theatre", "outpatient", "surgery", "patient care",
            "vital signs", "pharmacology", "icu", "cpr", "bls", "acls", "clinical documentation",
            "phlebotomy", "triage", "anatomy", "pathology", "nursing", "medical coding",
            "medication", "first aid", "pediatric", "oncology", "surgical", "anesthesia",
            "clinical research", "dialysis", "physiotherapy", "diagnostics", "immunization",
            "wound care", "emr", "ehr", "medical billing", "psychotherapy", "counseling",
        },
    },

    # ============================================================
    # SOFTWARE / TECH — core + sub-branches
    # ============================================================
    "tech": {
        "role_keywords": {
            "software", "developer", "engineer", "frontend", "backend", "fullstack", "full stack",
            "ml", "ai", "data", "devops", "cloud", "qa", "architect", "programmer", "cybersecurity",
            "network", "machine learning", "deep learning", "nlp", "system", "database", "sre",
            "web developer", "mobile developer", "ios", "android", "game developer", "blockchain",
        },
        "skill_keywords": {
            "python", "java", "c++", "javascript", "typescript", "react", "node", "sql", "pytorch",
            "tensorflow", "aws", "azure", "gcp", "docker", "kubernetes", "git", "linux", "pandas",
            "spark", "rest api", "html", "css", "c#", "ruby", "go", "rust", "nlp", "machine learning",
            "scikit-learn", "deep learning", "mongodb", "postgresql", "ci/cd", "devops", "django",
            "fastapi", "flask", "api", "tableau", "power bi", "keras", "r", "matlab", "graphql",
            "nextjs", "vue", "angular", "spring boot", "kafka", "redis", "terraform", "ansible",
            "unity", "unreal engine", "solidity", "penetration testing", "firewall",
        },
    },

    "frontend_engineering": {
        "role_keywords": {
            "frontend engineer", "ui engineer", "react developer", "vue developer",
            "angular developer", "web developer",
        },
        "skill_keywords": {
            "react", "vue", "angular", "webpack", "vite", "sass", "accessibility", "a11y",
            "responsive design", "web components", "html", "css", "typescript", "javascript",
        },
    },

    "backend_engineering": {
        "role_keywords": {
            "backend engineer", "api engineer", "microservices developer", "server-side developer",
        },
        "skill_keywords": {
            "grpc", "message queues", "rabbitmq", "kafka", "load balancing", "caching",
            "redis", "memcached", "rest api", "graphql", "microservices", "sql", "nosql",
        },
    },

    "devops_sre": {
        "role_keywords": {
            "devops engineer", "site reliability engineer", "sre", "platform engineer",
            "infrastructure engineer", "release engineer",
        },
        "skill_keywords": {
            "terraform", "ansible", "prometheus", "grafana", "helm", "argo cd", "kubernetes",
            "docker", "incident management", "on-call", "chaos engineering", "ci/cd",
        },
    },

    "cloud_engineering": {
        "role_keywords": {
            "cloud engineer", "cloud architect", "solutions architect", "aws engineer",
            "azure engineer", "gcp engineer",
        },
        "skill_keywords": {
            "aws", "azure", "gcp", "cloudformation", "lambda", "ec2", "s3", "iam", "vpc",
            "serverless architecture", "cloud migration", "cloud security",
        },
    },

    "data_engineering": {
        "role_keywords": {
            "data engineer", "etl developer", "big data engineer",
        },
        "skill_keywords": {
            "airflow", "dbt", "snowflake", "redshift", "databricks", "etl", "elt",
            "data lakes", "data warehousing", "spark", "hadoop", "sql",
        },
    },

    "data_science_ml": {
        "role_keywords": {
            "data scientist", "machine learning engineer", "ml engineer", "mlops engineer",
        },
        "skill_keywords": {
            "mlops", "model deployment", "feature engineering", "a/b testing", "xgboost",
            "llm fine-tuning", "vector databases", "rag pipelines", "prompt engineering",
            "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy",
        },
    },

    "ai_llm_engineering": {
        "role_keywords": {
            "ai engineer", "llm engineer", "generative ai engineer", "conversational ai engineer",
        },
        "skill_keywords": {
            "langchain", "llamaindex", "embeddings", "transformers", "huggingface",
            "agentic workflows", "prompt engineering", "vector databases", "rag pipelines",
        },
    },

    "cybersecurity": {
        "role_keywords": {
            "security analyst", "penetration tester", "soc analyst", "incident responder",
            "security architect", "cybersecurity engineer", "ethical hacker",
        },
        "skill_keywords": {
            "siem", "ids", "ips", "threat modeling", "owasp", "vulnerability assessment",
            "red team", "blue team", "iso 27001", "penetration testing", "firewall",
            "network security", "malware analysis",
        },
    },

    "qa_test_engineering": {
        "role_keywords": {
            "qa engineer", "test engineer", "sdet", "automation tester", "manual tester",
        },
        "skill_keywords": {
            "selenium", "cypress", "playwright", "postman", "test case design",
            "load testing", "jmeter", "test automation", "regression testing",
        },
    },

    "mobile_development": {
        "role_keywords": {
            "ios engineer", "android engineer", "mobile developer", "react native developer",
            "flutter developer",
        },
        "skill_keywords": {
            "swift", "kotlin", "xcode", "android studio", "dart", "flutter",
            "react native", "mobile ui patterns", "objective-c",
        },
    },

    "game_development": {
        "role_keywords": {
            "gameplay programmer", "graphics engineer", "tools engineer", "game developer",
        },
        "skill_keywords": {
            "unity", "unreal engine", "c++", "shader programming", "opengl", "directx",
            "game physics", "3d graphics programming",
        },
    },

    "blockchain_web3": {
        "role_keywords": {
            "blockchain developer", "smart contract developer", "blockchain architect",
            "web3 developer",
        },
        "skill_keywords": {
            "solidity", "ethereum", "web3.js", "smart contracts", "defi", "nfts",
            "consensus algorithms", "blockchain",
        },
    },

    "database_administration": {
        "role_keywords": {
            "database administrator", "dba", "database engineer",
        },
        "skill_keywords": {
            "query optimization", "replication", "backup and recovery", "oracle",
            "sql server", "indexing strategies", "postgresql", "mongodb",
        },
    },

    "it_support_sysadmin": {
        "role_keywords": {
            "it support specialist", "helpdesk technician", "system administrator",
            "network administrator", "it technician",
        },
        "skill_keywords": {
            "active directory", "windows server", "ticketing systems", "troubleshooting",
            "itil", "networking", "tcp/ip", "dns",
        },
    },

    "embedded_firmware": {
        "role_keywords": {
            "embedded software engineer", "firmware engineer",
        },
        "skill_keywords": {
            "rtos", "c", "c++", "device drivers", "bootloaders", "embedded systems",
            "microcontroller",
        },
    },

    "ar_vr_xr_development": {
        "role_keywords": {
            "ar developer", "vr developer", "xr developer", "spatial computing engineer",
        },
        "skill_keywords": {
            "unity xr", "oculus sdk", "spatial computing", "3d modeling for vr", "arkit", "arcore",
        },
    },

    "quantum_computing": {
        "role_keywords": {
            "quantum software engineer", "quantum computing researcher",
        },
        "skill_keywords": {
            "qiskit", "quantum algorithms", "linear algebra", "quantum circuits",
        },
    },

    # ============================================================
    # MECHANICAL ENGINEERING — core + sub-branches
    # ============================================================
    "mechanical_engineering": {
        "role_keywords": {
            "mechanical engineer", "design engineer", "product engineer", "manufacturing engineer",
            "hvac engineer", "maintenance engineer", "tool design engineer", "thermal engineer",
        },
        "skill_keywords": {
            "autocad", "solidworks", "catia", "ansys", "cad", "cam", "cnc", "gd&t",
            "thermodynamics", "fluid mechanics", "machine design", "fea", "6-sigma",
            "manufacturing processes", "heat transfer", "mechanics of materials",
            "pro-e", "creo", "3d modeling", "kinematics", "hvac design",
        },
    },

    "robotics_mechatronics": {
        "role_keywords": {
            "robotics engineer", "mechatronics engineer", "automation engineer",
        },
        "skill_keywords": {
            "ros", "robot kinematics", "sensor fusion", "plc", "embedded systems",
            "actuators", "control systems",
        },
    },

    "acoustics_tribology": {
        "role_keywords": {
            "acoustics engineer", "tribology engineer", "noise vibration harshness engineer",
        },
        "skill_keywords": {
            "noise and vibration analysis", "tribology", "acoustic modeling", "nvh testing",
        },
    },

    # ============================================================
    # CIVIL ENGINEERING — core + sub-branches
    # ============================================================
    "civil_engineering": {
        "role_keywords": {
            "civil engineer", "structural engineer", "site engineer", "construction engineer",
            "surveyor", "urban planner", "transportation engineer", "geotechnical engineer",
        },
        "skill_keywords": {
            "autocad", "staad pro", "revit", "structural analysis", "surveying",
            "construction management", "estimation and costing", "concrete technology",
            "building codes", "site supervision", "quantity surveying", "total station",
            "primavera", "ms project", "geotechnical analysis", "town planning",
        },
    },

    "water_resources_engineering": {
        "role_keywords": {
            "water resources engineer", "hydraulic engineer", "irrigation engineer",
        },
        "skill_keywords": {
            "hydrology", "hydraulic modeling", "water supply design", "flood analysis",
        },
    },

    "seismic_earthquake_engineering": {
        "role_keywords": {
            "seismic engineer", "earthquake engineer",
        },
        "skill_keywords": {
            "seismic analysis", "earthquake-resistant design", "structural dynamics",
        },
    },

    # ============================================================
    # ELECTRICAL ENGINEERING — core + sub-branches
    # ============================================================
    "electrical_engineering": {
        "role_keywords": {
            "electrical engineer", "power engineer", "control engineer", "instrumentation engineer",
            "substation engineer", "protection engineer",
        },
        "skill_keywords": {
            "circuit design", "power systems", "plc", "scada", "switchgear", "transformers",
            "electrical wiring", "matlab simulink", "autocad electrical", "relay coordination",
            "motor control", "vfd", "load flow analysis", "electrical safety", "power electronics",
        },
    },

    "renewable_energy_engineering": {
        "role_keywords": {
            "solar design engineer", "renewable energy engineer", "wind energy engineer",
            "battery storage engineer",
        },
        "skill_keywords": {
            "solar pv design", "wind turbine systems", "energy storage systems",
            "battery management system", "grid integration",
        },
    },

    # ============================================================
    # ELECTRONICS & COMMUNICATION — core + sub-branches
    # ============================================================
    "electronics_engineering": {
        "role_keywords": {
            "electronics engineer", "embedded engineer", "vlsi engineer", "hardware engineer",
            "rf engineer", "telecom engineer", "iot engineer",
        },
        "skill_keywords": {
            "embedded c", "microcontroller", "pcb design", "vlsi", "verilog", "vhdl",
            "arduino", "raspberry pi", "signal processing", "fpga", "arm", "iot",
            "rf design", "circuit simulation", "sensors", "eagle", "altium",
        },
    },

    "semiconductor_chip_design": {
        "role_keywords": {
            "analog design engineer", "asic design engineer", "semiconductor engineer",
            "chip design engineer", "hardware test engineer",
        },
        "skill_keywords": {
            "asic design", "analog circuit design", "semiconductor fabrication",
            "chip verification", "spice simulation",
        },
    },

    # ============================================================
    # CHEMICAL ENGINEERING
    # ============================================================
    "chemical_engineering": {
        "role_keywords": {
            "chemical engineer", "process engineer", "petrochemical engineer",
            "refinery engineer", "plant engineer",
        },
        "skill_keywords": {
            "process design", "mass transfer", "reaction engineering", "distillation",
            "piping and instrumentation diagram", "p&id", "aspen plus", "hysys",
            "process safety", "chemical plant operations", "heat exchangers", "catalysis",
        },
    },

    # ============================================================
    # AEROSPACE ENGINEERING
    # ============================================================
    "aerospace_engineering": {
        "role_keywords": {
            "aerospace engineer", "aeronautical engineer", "avionics engineer",
            "flight test engineer", "propulsion engineer",
        },
        "skill_keywords": {
            "aerodynamics", "propulsion", "flight mechanics", "avionics", "cad for aerospace",
            "cfd", "structural analysis", "aircraft systems", "composite materials",
            "matlab", "catia", "ansys fluent",
        },
    },

    # ============================================================
    # AUTOMOBILE ENGINEERING
    # ============================================================
    "automobile_engineering": {
        "role_keywords": {
            "automobile engineer", "automotive engineer", "vehicle design engineer",
            "powertrain engineer", "chassis engineer",
        },
        "skill_keywords": {
            "vehicle dynamics", "engine design", "transmission systems", "catia",
            "automotive electronics", "powertrain", "chassis design", "ev technology",
            "battery management system", "diagnostics tools", "obd",
        },
    },

    # ============================================================
    # INDUSTRIAL / PRODUCTION ENGINEERING
    # ============================================================
    "industrial_engineering": {
        "role_keywords": {
            "industrial engineer", "production engineer", "operations engineer",
            "process improvement engineer", "plant manager",
        },
        "skill_keywords": {
            "lean manufacturing", "six sigma", "kaizen", "process optimization",
            "supply chain", "inventory management", "erp", "production planning",
            "quality control", "root cause analysis", "time and motion study",
        },
    },

    # ============================================================
    # BIOMEDICAL ENGINEERING
    # ============================================================
    "biomedical_engineering": {
        "role_keywords": {
            "biomedical engineer", "clinical engineer", "medical device engineer",
            "biotech engineer",
        },
        "skill_keywords": {
            "medical imaging", "biomechanics", "medical device design", "biosensors",
            "regulatory affairs", "fda compliance", "prosthetics design", "biomaterials",
        },
    },

    # ============================================================
    # ENVIRONMENTAL ENGINEERING
    # ============================================================
    "environmental_engineering": {
        "role_keywords": {
            "environmental engineer", "sustainability engineer", "pollution control engineer",
            "waste management engineer",
        },
        "skill_keywords": {
            "environmental impact assessment", "waste management", "water treatment",
            "air quality monitoring", "sustainability", "gis", "environmental compliance",
        },
    },

    # ============================================================
    # NEW ENGINEERING BRANCHES (previously missing)
    # ============================================================
    "petroleum_mining_engineering": {
        "role_keywords": {
            "petroleum engineer", "drilling engineer", "reservoir engineer",
            "mining engineer", "mineral processing engineer",
        },
        "skill_keywords": {
            "reservoir simulation", "drilling operations", "mine planning",
            "mineral extraction", "well logging",
        },
    },

    "marine_naval_engineering": {
        "role_keywords": {
            "naval architect", "marine engineer", "offshore engineer",
        },
        "skill_keywords": {
            "ship design", "offshore structures", "marine propulsion systems",
            "hull design", "marine surveying",
        },
    },

    "metallurgical_materials_engineering": {
        "role_keywords": {
            "metallurgist", "materials scientist", "welding engineer", "materials engineer",
        },
        "skill_keywords": {
            "metallurgy", "alloy design", "heat treatment", "materials testing",
            "corrosion analysis", "welding processes",
        },
    },

    "textile_engineering": {
        "role_keywords": {
            "textile engineer", "fabric technologist",
        },
        "skill_keywords": {
            "yarn technology", "weaving", "textile testing", "dyeing and finishing",
        },
    },

    "nuclear_engineering": {
        "role_keywords": {
            "nuclear engineer", "radiation safety officer",
        },
        "skill_keywords": {
            "reactor design", "radiation protection", "nuclear safety systems",
            "nuclear fuel cycle",
        },
    },

    "safety_engineering_ehs": {
        "role_keywords": {
            "safety engineer", "hse officer", "ehs specialist", "occupational safety officer",
        },
        "skill_keywords": {
            "hazard analysis", "osha compliance", "risk assessment", "safety audits",
            "incident investigation",
        },
    },

    "systems_engineering": {
        "role_keywords": {
            "systems engineer",
        },
        "skill_keywords": {
            "requirements engineering", "systems integration",
            "model-based systems engineering", "mbse",
        },
    },

    # ============================================================
    # COMPUTER SCIENCE ADJACENT: DATA/RESEARCH SCIENCE
    # ============================================================
    "science_research": {
        "role_keywords": {
            "research scientist", "physicist", "chemist", "biologist", "lab technician",
            "research analyst", "scientific officer",
        },
        "skill_keywords": {
            "research methodology", "lab techniques", "data analysis", "spectroscopy",
            "chromatography", "microscopy", "statistical analysis", "scientific writing",
            "experiment design", "r", "spss",
        },
    },

    "astronomy_space": {
        "role_keywords": {
            "astronomer", "aerospace mission analyst", "satellite operations specialist",
        },
        "skill_keywords": {
            "orbital mechanics", "satellite systems", "astrophysics", "telescope operations",
        },
    },

    # ============================================================
    # FINANCE / COMMERCE
    # ============================================================
    "finance": {
        "role_keywords": {
            "accountant", "auditor", "finance", "financial", "tax", "bookkeeper", "banking",
            "treasury", "actuary", "investment analyst", "credit analyst", "loan officer",
        },
        "skill_keywords": {
            "accounting", "taxation", "gaap", "ifrs", "financial modeling", "auditing",
            "quickbooks", "tally", "sap fi", "payroll", "financial reporting", "bookkeeping",
            "tax", "valuation", "portfolio management", "equity research", "excel",
            "budgeting", "risk management",
        },
    },

    # ============================================================
    # BANKING & INSURANCE (distinct from general finance)
    # ============================================================
    "banking_insurance": {
        "role_keywords": {
            "bank teller", "relationship manager", "underwriter", "claims adjuster",
            "insurance agent", "insurance broker", "risk analyst", "compliance officer",
            "credit risk manager", "mortgage broker",
        },
        "skill_keywords": {
            "underwriting", "claims processing", "policy administration", "credit risk analysis",
            "kyc", "aml compliance", "loan origination", "actuarial analysis",
        },
    },

    # ============================================================
    # REAL ESTATE
    # ============================================================
    "real_estate": {
        "role_keywords": {
            "real estate agent", "real estate broker", "property manager", "appraiser",
            "leasing consultant", "real estate developer", "facilities manager",
        },
        "skill_keywords": {
            "property valuation", "lease negotiation", "property management",
            "real estate law", "market analysis", "facilities management",
        },
    },

    # ============================================================
    # RETAIL & E-COMMERCE
    # ============================================================
    "retail_ecommerce": {
        "role_keywords": {
            "retail associate", "store manager", "merchandiser", "category manager",
            "e-commerce manager", "buyer", "purchasing agent", "visual merchandiser",
        },
        "skill_keywords": {
            "merchandising", "inventory management", "point of sale", "pos systems",
            "marketplace operations", "category management", "visual merchandising",
        },
    },

    # ============================================================
    # CUSTOMER SERVICE / BPO
    # ============================================================
    "customer_service_bpo": {
        "role_keywords": {
            "customer support representative", "call center agent", "technical support specialist",
            "customer success manager",
        },
        "skill_keywords": {
            "customer service", "crm", "ticketing systems", "conflict resolution",
            "call handling", "customer retention",
        },
    },

    # ============================================================
    # PUBLIC ADMINISTRATION & GOVERNMENT
    # ============================================================
    "public_administration_government": {
        "role_keywords": {
            "civil servant", "policy analyst", "urban planner", "diplomat",
            "foreign service officer", "public administrator", "tax officer", "government auditor",
        },
        "skill_keywords": {
            "policy analysis", "public administration", "government relations",
            "regulatory compliance", "grant management",
        },
    },

    # ============================================================
    # MILITARY & DEFENSE
    # ============================================================
    "military_defense": {
        "role_keywords": {
            "military officer", "defense analyst", "intelligence officer",
        },
        "skill_keywords": {
            "strategic planning", "defense operations", "intelligence analysis",
            "tactical operations",
        },
    },

    # ============================================================
    # NON-PROFIT & SOCIAL SERVICES
    # ============================================================
    "nonprofit_social_services": {
        "role_keywords": {
            "social worker", "case manager", "community organizer", "ngo program officer",
            "fundraiser", "development officer", "humanitarian aid worker",
        },
        "skill_keywords": {
            "case management", "community outreach", "grant writing", "fundraising",
            "program management", "needs assessment",
        },
    },

    # ============================================================
    # RELIGIOUS / CLERGY
    # ============================================================
    "religious_clergy": {
        "role_keywords": {
            "priest", "pastor", "imam", "rabbi", "chaplain", "missionary", "religious educator",
        },
        "skill_keywords": {
            "pastoral care", "religious education", "community ministry", "counseling",
        },
    },

    # ============================================================
    # LIBRARY, ARCHIVES & INFORMATION SCIENCE
    # ============================================================
    "library_archives": {
        "role_keywords": {
            "librarian", "archivist", "records manager", "museum curator",
        },
        "skill_keywords": {
            "cataloging", "archival research", "records management", "digital archiving",
            "curation",
        },
    },

    # ============================================================
    # TRANSLATION & LANGUAGE SERVICES
    # ============================================================
    "translation_language_services": {
        "role_keywords": {
            "translator", "interpreter", "localization specialist", "linguist",
        },
        "skill_keywords": {
            "translation", "interpretation", "localization", "cat tools",
            "multilingual communication",
        },
    },

    # ============================================================
    # MARITIME & TRANSPORTATION (non-aviation)
    # ============================================================
    "maritime_transportation": {
        "role_keywords": {
            "ship captain", "marine officer", "merchant mariner", "port operations manager",
            "railway engineer", "railway operator", "truck driver", "fleet driver",
            "transportation planner",
        },
        "skill_keywords": {
            "navigation", "maritime safety", "port operations", "railway operations",
            "fleet management", "route planning",
        },
    },

    # ============================================================
    # TEXTILE, FASHION & APPAREL
    # ============================================================
    "fashion_apparel": {
        "role_keywords": {
            "fashion designer", "textile designer", "pattern maker", "fashion merchandiser",
            "garment technologist",
        },
        "skill_keywords": {
            "fashion design", "pattern making", "textile design", "garment construction",
            "trend forecasting",
        },
    },

    # ============================================================
    # BEAUTY & PERSONAL CARE
    # ============================================================
    "beauty_personal_care": {
        "role_keywords": {
            "cosmetologist", "hairstylist", "esthetician", "makeup artist",
            "nail technician", "massage therapist",
        },
        "skill_keywords": {
            "hairstyling", "skincare treatments", "makeup application", "nail care",
            "massage techniques",
        },
    },

    # ============================================================
    # FUNERAL & MORTUARY SERVICES
    # ============================================================
    "funeral_mortuary_services": {
        "role_keywords": {
            "funeral director", "mortician", "embalmer",
        },
        "skill_keywords": {
            "embalming", "funeral arrangement", "grief support", "mortuary science",
        },
    },

    # ============================================================
    # FOOD SCIENCE & PRODUCTION (distinct from culinary)
    # ============================================================
    "food_science_production": {
        "role_keywords": {
            "food scientist", "food technologist", "quality control food industry",
            "brewmaster", "winemaker",
        },
        "skill_keywords": {
            "food safety standards", "food product development", "sensory analysis",
            "fermentation science", "haccp",
        },
    },

    # ============================================================
    # FORESTRY & FISHERIES
    # ============================================================
    "forestry_fisheries": {
        "role_keywords": {
            "forester", "fisheries officer", "wildlife biologist", "park ranger",
            "conservation officer",
        },
        "skill_keywords": {
            "forest management", "wildlife conservation", "fisheries management",
            "habitat assessment", "gis",
        },
    },

    # ============================================================
    # GAMING & ESPORTS (distinct from game_development)
    # ============================================================
    "gaming_esports": {
        "role_keywords": {
            "game designer", "esports player", "esports coach", "game tester",
            "streamer", "content creator gaming",
        },
        "skill_keywords": {
            "game design", "esports strategy", "game testing", "live streaming",
            "content creation",
        },
    },

    # ============================================================
    # CONSULTING & PROJECT MANAGEMENT
    # ============================================================
    "consulting_project_management": {
        "role_keywords": {
            "management consultant", "strategy consultant", "project manager",
            "scrum master", "agile coach", "business analyst",
        },
        "skill_keywords": {
            "project management", "pmp", "agile", "scrum", "stakeholder management",
            "business analysis", "strategic planning",
        },
    },

    # ============================================================
    # QUALITY, COMPLIANCE & AUDIT (cross-industry)
    # ============================================================
    "quality_compliance_audit": {
        "role_keywords": {
            "quality assurance manager", "iso compliance officer", "internal auditor",
            "regulatory affairs specialist",
        },
        "skill_keywords": {
            "iso standards", "internal auditing", "regulatory compliance",
            "quality management systems", "process audits",
        },
    },

    # ============================================================
    # LEGAL
    # ============================================================
    "legal": {
        "role_keywords": {
            "lawyer", "attorney", "paralegal", "legal", "counsel", "litigator", "solicitor",
            "barrister", "legal advisor",
        },
        "skill_keywords": {
            "litigation", "contract drafting", "legal research", "compliance", "brief writing",
            "tort law", "intellectual property", "corporate law", "legal writing",
            "case management", "negotiation",
        },
    },

    # ============================================================
    # CULINARY
    # ============================================================
    "culinary": {
        "role_keywords": {
            "chef", "cook", "baker", "sous chef", "pastry", "bartender", "kitchen", "culinary",
        },
        "skill_keywords": {
            "cooking", "baking", "knife skills", "food safety", "haccp", "menu planning",
            "grilling", "plating", "pastry", "culinary", "food preparation", "bartending",
        },
    },

    # ============================================================
    # TRADES
    # ============================================================
    "trades": {
        "role_keywords": {
            "electrician", "plumber", "carpenter", "mechanic", "welder", "hvac", "machinist",
            "fitter", "technician",
        },
        "skill_keywords": {
            "welding", "pipefitting", "plumbing", "carpentry", "engine repair", "hvac",
            "electrical wiring", "machining", "soldering", "blueprint reading",
        },
    },

    # ============================================================
    # EDUCATION
    # ============================================================
    "education": {
        "role_keywords": {
            "teacher", "professor", "lecturer", "tutor", "educator", "principal",
            "academic counselor", "trainer",
        },
        "skill_keywords": {
            "lesson planning", "curriculum design", "classroom management", "pedagogy",
            "assessment design", "e-learning", "public speaking", "mentoring",
        },
    },

    # ============================================================
    # MARKETING / SALES
    # ============================================================
    "marketing_sales": {
        "role_keywords": {
            "marketing", "sales", "business development", "brand manager", "digital marketer",
            "sales executive", "account manager", "growth marketer",
        },
        "skill_keywords": {
            "seo", "sem", "social media marketing", "content marketing", "google ads",
            "crm", "salesforce", "market research", "email marketing", "branding",
            "negotiation", "lead generation", "google analytics",
        },
    },

    # ============================================================
    # HUMAN RESOURCES
    # ============================================================
    "human_resources": {
        "role_keywords": {
            "hr", "human resources", "recruiter", "talent acquisition", "hr manager",
            "hr generalist", "payroll specialist",
        },
        "skill_keywords": {
            "recruitment", "onboarding", "payroll management", "employee relations",
            "performance management", "hris", "talent management", "labor law",
        },
    },

    # ============================================================
    # DESIGN (UI/UX, GRAPHIC)
    # ============================================================
    "design": {
        "role_keywords": {
            "graphic designer", "ui designer", "ux designer", "product designer",
            "visual designer", "animator", "illustrator",
        },
        "skill_keywords": {
            "figma", "adobe photoshop", "adobe illustrator", "adobe xd", "sketch",
            "wireframing", "prototyping", "typography", "user research", "after effects",
            "canva", "3d animation",
        },
    },

    # ============================================================
    # ARCHITECTURE
    # ============================================================
    "architecture": {
        "role_keywords": {
            "architect", "interior designer", "landscape architect", "urban designer",
        },
        "skill_keywords": {
            "autocad", "revit", "sketchup", "3d rendering", "building design",
            "space planning", "vastu", "construction drawings", "lumion",
        },
    },

    # ============================================================
    # MEDIA / JOURNALISM
    # ============================================================
    "media_journalism": {
        "role_keywords": {
            "journalist", "content writer", "editor", "news anchor", "reporter",
            "copywriter", "video editor", "social media manager",
        },
        "skill_keywords": {
            "content writing", "editing", "storytelling", "video editing", "premiere pro",
            "final cut pro", "journalism", "public relations", "copywriting", "scriptwriting",
        },
    },

    # ============================================================
    # AGRICULTURE
    # ============================================================
    "agriculture": {
        "role_keywords": {
            "farmer", "agronomist", "agricultural officer", "horticulturist",
            "agricultural engineer", "farm manager",
        },
        "skill_keywords": {
            "crop management", "soil science", "irrigation", "pest management",
            "farm equipment operation", "horticulture", "agronomy", "precision farming",
        },
    },

    # ============================================================
    # HOSPITALITY / TOURISM
    # ============================================================
    "hospitality_tourism": {
        "role_keywords": {
            "hotel manager", "front office executive", "housekeeping", "tour guide",
            "travel agent", "event manager", "cabin crew",
        },
        "skill_keywords": {
            "guest relations", "front office management", "event planning",
            "reservation systems", "customer service", "travel planning", "hospitality management",
        },
    },

    # ============================================================
    # LOGISTICS / SUPPLY CHAIN
    # ============================================================
    "logistics_supply_chain": {
        "role_keywords": {
            "logistics manager", "supply chain analyst", "warehouse manager",
            "procurement officer", "fleet manager",
        },
        "skill_keywords": {
            "inventory management", "warehouse management", "sap", "procurement",
            "demand forecasting", "route planning", "erp", "vendor management",
        },
    },

    # ============================================================
    # LAW ENFORCEMENT / SECURITY
    # ============================================================
    "law_enforcement_security": {
        "role_keywords": {
            "police officer", "security guard", "detective", "forensic analyst",
            "security manager",
        },
        "skill_keywords": {
            "surveillance", "investigation", "forensic analysis", "crime scene analysis",
            "security operations", "risk assessment", "crowd control",
        },
    },

    # ============================================================
    # AVIATION (non-engineering)
    # ============================================================
    "aviation": {
        "role_keywords": {
            "pilot", "cabin crew", "air traffic controller", "flight dispatcher",
            "ground staff",
        },
        "skill_keywords": {
            "flight operations", "aviation safety", "navigation", "air traffic control",
            "customer service", "emergency procedures",
        },
    },

    # ============================================================
    # PERFORMING ARTS / SPORTS
    # ============================================================
    "arts_sports": {
        "role_keywords": {
            "musician", "dancer", "actor", "athlete", "coach", "fitness trainer",
            "choreographer", "sports coach",
        },
        "skill_keywords": {
            "choreography", "performance", "vocal training", "strength training",
            "coaching", "sports psychology", "nutrition planning", "fitness assessment",
        },
    },
}

def check_skill_role_mismatch(role: str, skills: Sequence[str] | None) -> bool:
    if not skills:
        return False

    role_lower = role.lower()
    skill_lowers = [s.lower().strip() for s in skills if s.strip()]
    if not skill_lowers:
        return False

    role_domains = set()
    role_tokens = set(re.split(r"[\s/,-]+", role_lower))
    for domain, profile in _DOMAIN_PROFILES.items():
        if any(rk in role_lower or rk in role_tokens for rk in profile["role_keywords"]):
            role_domains.add(domain)

    if not role_domains:
        return False

    skill_domains = set()
    for s in skill_lowers:
        s_tokens = set(re.split(r"[\s/,-]+", s))
        for domain, profile in _DOMAIN_PROFILES.items():
            if s in profile["skill_keywords"] or any(sk in s or sk in s_tokens for sk in profile["skill_keywords"]):
                skill_domains.add(domain)

    if skill_domains and not (skill_domains & role_domains):
        return True

    return False


def validate_skill_role_compatibility(role: str, skills: Sequence[str] | None) -> None:
    """Validate that the provided skills are compatible with the requested job role."""
    if not skills:
        return
    cleaned_skills = [s.strip() for s in skills if s.strip()]
    if not cleaned_skills:
        return

    if check_skill_role_mismatch(role, cleaned_skills):
        raise JobSearchError(
            "The skills do not match the job role. Please provide skills relevant to your target role."
        )


# --------------------------------------------------------------------------
# 1. Job Search Tool
# --------------------------------------------------------------------------


@traceable(name="search_jobs", run_type="tool")
def search_jobs(
    role: str,
    settings: Settings,
    *,
    skills: Sequence[str] | None = None,
    location: str | None = None,
    experience_level: str | None = None,
    limit: int | None = None,
) -> list[JobListing]:
    """Search jobs by role, skills, location, and experience level.

    Uses the Adzuna API when credentials are configured (`Settings.has_job_search_api`),
    otherwise filters the small bundled sample dataset — so this tool always
    returns something usable, even with zero external configuration.
    """
    role = (role or "").strip()
    if not role:
        raise JobSearchError("Please provide a job role or title to search for.")

    validate_skill_role_compatibility(role, skills)

    limit = limit or settings.job_search_default_limit

    if settings.has_job_search_api:
        try:
            return _search_jobs_adzuna(
                role, settings, skills=skills, location=location, limit=limit
            )
        except Exception as exc:
            logger.warning("Adzuna job search failed, falling back to bundled dataset: %s", exc)

    return _search_jobs_bundled(
        role, skills=skills, location=location, experience_level=experience_level, limit=limit
    )


# Region mappings for Adzuna API
_INDIA_LOCATIONS = {
    "india", "in", "bangalore", "bengaluru", "mumbai", "delhi", "new delhi", "ncr", "hyderabad",
    "pune", "chennai", "noida", "gurgaon", "gurugram", "kolkata", "ahmedabad", "jaipur", "kerala", "kochi",
}
_US_LOCATIONS = {
    "us", "usa", "united states", "america", "san francisco", "sf", "bay area", "california", "ca",
    "new york", "nyc", "ny", "seattle", "wa", "austin", "texas", "tx", "boston", "chicago", "los angeles",
    "la", "remote us", "silicon valley", "atlanta", "denver",
}
_EUROPE_LOCATIONS = {
    "europe", "european", "european countries", "eu", "uk", "gb", "united kingdom", "great britain",
    "england", "london", "manchester", "birmingham", "edinburgh", "germany", "deutschland", "de",
    "berlin", "munich", "frankfurt", "hamburg", "france", "fr", "paris", "lyon", "netherlands",
    "holland", "nl", "amsterdam", "rotterdam", "spain", "es", "madrid", "barcelona", "italy", "it",
    "milan", "rome", "poland", "pl", "warsaw", "krakow", "switzerland", "ch", "zurich", "austria",
    "at", "vienna", "belgium", "be", "brussels", "ireland", "ie", "dublin",
}


def _resolve_adzuna_countries(location: str | None, default_country: str) -> list[str]:
    loc = (location or "").lower().strip()
    if not loc:
        # User requested 3 core regions: India, US, Europe
        return ["in", "us", "gb", "de"]

    tokens = set(re.split(r"[\s,/-]+", loc))

    # Check for specific countries/cities
    if tokens & _INDIA_LOCATIONS or any(k in loc for k in ["india", "bangalore", "hyderabad", "mumbai", "delhi", "pune"]):
        return ["in"]
    if tokens & _US_LOCATIONS or any(k in loc for k in ["united states", "san francisco", "new york", "bay area"]):
        return ["us"]
    if any(k in loc for k in ["uk", "united kingdom", "great britain", "london", "england"]):
        return ["gb"]
    if any(k in loc for k in ["germany", "deutschland", "berlin", "munich", "frankfurt"]):
        return ["de"]
    if any(k in loc for k in ["france", "paris", "lyon"]):
        return ["fr"]
    if any(k in loc for k in ["netherlands", "holland", "amsterdam"]):
        return ["nl"]
    if any(k in loc for k in ["poland", "warsaw", "krakow"]):
        return ["pl"]
    if any(k in loc for k in ["spain", "madrid", "barcelona"]):
        return ["es"]
    if any(k in loc for k in ["italy", "milan", "rome"]):
        return ["it"]
    if any(k in loc for k in ["europe", "european", "eu"]):
        return ["gb", "de", "fr", "nl", "es", "it", "pl"]

    # Fallback default: multi-region search across India, US, and Europe
    if default_country and default_country in {"in", "us", "gb", "de", "fr", "nl", "ca", "au"}:
        return [default_country, "in", "us", "gb"]
    return ["in", "us", "gb", "de"]


def _search_jobs_adzuna(
    role: str,
    settings: Settings,
    *,
    skills: Sequence[str] | None,
    location: str | None,
    limit: int,
) -> list[JobListing]:
    import requests

    raw_country = (settings.job_search_country or "in").strip().lower()
    target_countries = _resolve_adzuna_countries(location, raw_country)
    loc_clean = (location or "").strip().lower()

    # Determine if 'where' is a generic region name or a specific city
    is_broad_region = loc_clean in {
        "", "all", "global", "remote", "worldwide", "india", "in", "us", "usa",
        "united states", "europe", "european", "european countries", "eu",
    }
    where_param = None if is_broad_region else location

    listings: list[JobListing] = []
    seen_urls: set[str] = set()
    per_country_limit = max(limit // len(target_countries), 3)

    for country in target_countries:
        # Build query candidates: try (role + 1st skill), then just (role)
        query_candidates = []
        if skills and len(skills) > 0:
            query_candidates.append(f"{role} {skills[0]}".strip())
        query_candidates.append(role.strip())

        for query_str in query_candidates:
            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
            params: dict[str, Any] = {
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "what": query_str,
                "results_per_page": min(per_country_limit, 50),
            }
            if where_param:
                params["where"] = where_param

            try:
                response = requests.get(url, params=params, timeout=settings.llm_request_timeout_seconds)
                if response.status_code == 200:
                    payload = response.json()
                    results = payload.get("results", [])
                    for item in results:
                        redirect_url = item.get("redirect_url", "")
                        if redirect_url and redirect_url in seen_urls:
                            continue
                        seen_urls.add(redirect_url)

                        raw_loc = (item.get("location") or {}).get("display_name", "Unspecified")
                        country_label = {
                            "in": "India",
                            "us": "US",
                            "gb": "UK",
                            "de": "Germany",
                            "fr": "France",
                            "nl": "Netherlands",
                            "es": "Spain",
                            "it": "Italy",
                            "pl": "Poland",
                        }.get(country, country.upper())

                        # Ensure country context in location display if not present
                        display_location = raw_loc
                        if country_label not in raw_loc:
                            display_location = f"{raw_loc} ({country_label})"

                        listings.append(
                            JobListing(
                                title=item.get("title", "Untitled role"),
                                company=(item.get("company") or {}).get("display_name", "Unknown company"),
                                location=display_location,
                                url=redirect_url,
                                description=(item.get("description") or "")[:500],
                                skills=list(skills or []),
                                experience_level=None,
                                source=f"adzuna-{country}",
                            )
                        )
                    if results:
                        break  # Found results for this country, proceed to next country
            except Exception as exc:
                logger.warning("Adzuna search error for country %s: %s", country, exc)

        if len(listings) >= limit:
            break

    if not listings:
        # Fallback to bundled dataset so user never receives 0 results
        return _search_jobs_bundled(role, skills=skills, location=location, experience_level=None, limit=limit)

    return listings[:limit]


def _search_jobs_bundled(
    role: str,
    *,
    skills: Sequence[str] | None,
    location: str | None,
    experience_level: str | None,
    limit: int,
) -> list[JobListing]:
    role_terms = {t for t in re.split(r"\s+", role.lower()) if t}
    skill_terms = {s.lower().strip() for s in (skills or []) if s.strip()}
    location_term = (location or "").lower().strip()
    experience_term = (experience_level or "").lower().strip()

    scored: list[tuple[float, dict]] = []
    for job in SAMPLE_JOBS:
        title_terms = set(re.split(r"\s+", job["title"].lower()))
        job_skills = {s.lower() for s in job["skills"]}

        role_score = len(role_terms & title_terms) / max(len(role_terms), 1)
        skill_score = (
            len(skill_terms & job_skills) / max(len(skill_terms), 1) if skill_terms else 0.0
        )

        if (
            location_term
            and location_term not in job["location"].lower()
            and location_term != "remote"
        ):
            continue
        if location_term == "remote" and job["location"].lower() != "remote":
            continue
        if experience_term and experience_term != job["experience_level"]:
            continue

        score = role_score + skill_score
        if role_score == 0 and skill_score == 0:
            continue
        scored.append((score, job))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    results = [job for _, job in scored[:limit]]

    return [
        JobListing(
            title=job["title"],
            company=job["company"],
            location=job["location"],
            url=job["url"],
            description=job["description"],
            skills=job["skills"],
            experience_level=job["experience_level"],
            source="bundled",
        )
        for job in results
    ]


# --------------------------------------------------------------------------
# 2. Skill Gap Analyzer
# --------------------------------------------------------------------------


@traceable(name="analyze_skill_gap", run_type="chain")
def analyze_skill_gap(
    user_skills: Sequence[str], target_role: str, llm: LLMProvider
) -> SkillGapResult:
    """Compare a user's current skills against a target role using the LLM."""
    target_role = (target_role or "").strip()
    if not target_role:
        raise LLMError("Please provide a target role to compare skills against.")
    skills_text = ", ".join(s.strip() for s in user_skills if s.strip()) or "(none provided)"

    prompt = (
        "You are a career-skills analyst. Compare the candidate's current "
        f"skills against what is typically required for the target role.\n\n"
        f"Target role: {target_role}\n"
        f"Candidate's current skills: {skills_text}\n\n"
        "Respond with ONLY a JSON object (no markdown, no commentary) with exactly "
        "these keys:\n"
        '  "matched_skills": array of the candidate\'s skills that are relevant to the role,\n'
        '  "missing_skills": array of important skills for the role the candidate does not have,\n'
        '  "partially_met_skills": array of skills the candidate has some but not full proficiency in,\n'
        '  "overall_readiness": one of "low", "medium", "high",\n'
        '  "summary": a 2-3 sentence plain-language summary.'
    )

    data = _generate_json(llm, prompt)
    return SkillGapResult(
        matched_skills=_as_str_list(data.get("matched_skills")),
        missing_skills=_as_str_list(data.get("missing_skills")),
        partially_met_skills=_as_str_list(data.get("partially_met_skills")),
        overall_readiness=str(data.get("overall_readiness", "medium")).lower(),
        summary=str(data.get("summary", "")).strip(),
    )


# --------------------------------------------------------------------------
# 3. Resume Analyzer
# --------------------------------------------------------------------------


@traceable(name="analyze_resume", run_type="chain")
def analyze_resume(
    resume_text: str, llm: LLMProvider, *, target_role: str | None = None
) -> ResumeAnalysis:
    """Extract skills from resume text and identify missing/improvable areas.

    If `target_role` is given, gaps and suggested roles are framed relative
    to it; otherwise the model infers plausible target roles itself.
    """
    resume_text = (resume_text or "").strip()
    if not resume_text:
        raise LLMError("The resume appears to be empty — no text could be analyzed.")

    role_instruction = (
        f'Evaluate the resume specifically against this target role: "{target_role.strip()}".'
        if target_role and target_role.strip()
        else "Suggest 2-4 target roles the candidate is well-suited for based on the resume."
    )

    prompt = (
        "You are a resume reviewer for a career-advising assistant. Read the resume "
        f"text below and extract structured information. {role_instruction}\n\n"
        f'Resume text:\n"""\n{resume_text[:12000]}\n"""\n\n'
        "Respond with ONLY a JSON object (no markdown, no commentary) with exactly "
        "these keys:\n"
        '  "extracted_skills": array of skills found or reasonably implied in the resume,\n'
        '  "experience_summary": a 2-3 sentence summary of the candidate\'s experience level and background,\n'
        '  "strengths": array of notable strengths,\n'
        '  "gaps_or_improvements": array of missing skills, weak areas, or resume-writing improvements,\n'
        '  "suggested_target_roles": array of role titles this candidate is or could become well-suited for.'
    )

    data = _generate_json(llm, prompt)
    return ResumeAnalysis(
        extracted_skills=_as_str_list(data.get("extracted_skills")),
        experience_summary=str(data.get("experience_summary", "")).strip(),
        strengths=_as_str_list(data.get("strengths")),
        gaps_or_improvements=_as_str_list(data.get("gaps_or_improvements")),
        suggested_target_roles=_as_str_list(data.get("suggested_target_roles")),
    )


# --------------------------------------------------------------------------
# 4. Career Roadmap Generator
# --------------------------------------------------------------------------


@traceable(name="generate_roadmap", run_type="chain")
def generate_roadmap(
    current_skills: Sequence[str],
    target_role: str,
    llm: LLMProvider,
    *,
    timeframe_months: int = 6,
) -> RoadmapResult:
    """Generate a structured, milestone-based learning roadmap toward `target_role`."""
    target_role = (target_role or "").strip()
    if not target_role:
        raise LLMError("Please provide a target role to build a roadmap toward.")
    skills_text = ", ".join(s.strip() for s in current_skills if s.strip()) or "(none provided)"
    timeframe_months = max(1, min(int(timeframe_months or 6), 36))

    prompt = (
        "You are a career coach building a structured learning roadmap.\n\n"
        f"Target role: {target_role}\n"
        f"Candidate's current skills: {skills_text}\n"
        f"Desired timeframe: {timeframe_months} months\n\n"
        "Break the timeframe into 3-5 sequential milestones. Respond with ONLY a "
        "JSON object (no markdown, no commentary) with exactly these keys:\n"
        '  "milestones": array of objects, each with "title" (string), "duration" '
        '(e.g. "Weeks 1-4"), "focus_skills" (array of strings), and "actions" '
        "(array of 2-4 concrete action strings),\n"
        '  "summary": a 2-3 sentence overview of the roadmap.'
    )

    data = _generate_json(llm, prompt)
    milestones = [
        RoadmapMilestone(
            title=str(m.get("title", "")).strip(),
            duration=str(m.get("duration", "")).strip(),
            focus_skills=_as_str_list(m.get("focus_skills")),
            actions=_as_str_list(m.get("actions")),
        )
        for m in (data.get("milestones") or [])
        if isinstance(m, dict)
    ]
    return RoadmapResult(
        target_role=target_role,
        milestones=milestones,
        summary=str(data.get("summary", "")).strip(),
    )

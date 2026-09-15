'use client';

import React, { useEffect, useState } from 'react';

interface MascotProps {
  size?: number;
  className?: string;
  statusText?: string;
}

export const Mascot: React.FC<MascotProps> = ({ size = 260, className = '' }) => {
  const [isBlinking, setIsBlinking] = useState(false);

  useEffect(() => {
    let blinkTimeoutId: ReturnType<typeof setTimeout>;
    let nextBlinkTimeoutId: ReturnType<typeof setTimeout>;

    const scheduleNextBlink = () => {
      // Random interval between 3000ms (3s) and 6000ms (6s)
      const delay = 3000 + Math.random() * 3000;
      nextBlinkTimeoutId = setTimeout(() => {
        setIsBlinking(true);
        // Blink duration is 140ms
        blinkTimeoutId = setTimeout(() => {
          setIsBlinking(false);
          scheduleNextBlink();
        }, 140);
      }, delay);
    };

    scheduleNextBlink();

    return () => {
      clearTimeout(blinkTimeoutId);
      clearTimeout(nextBlinkTimeoutId);
    };
  }, []);

  // SVG viewBox: 300 x 200 centered at (150, 100)
  return (
    <div
      className={`mascot-container ${className}`}
      style={{
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: `${size}px`,
        height: `${Math.round(size * 0.68)}px`,
        margin: '0 auto',
        userSelect: 'none',
      }}
    >
      <svg
        viewBox="0 0 300 200"
        width="100%"
        height="100%"
        style={{ overflow: 'visible' }}
        role="img"
        aria-label="CareerAI Mascot"
      >
        <defs>
          {/* Golden radial aura for outer glow */}
          <radialGradient id="mascotAura" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#D6A936" stopOpacity="0.4" />
            <stop offset="50%" stopColor="#D6A936" stopOpacity="0.12" />
            <stop offset="100%" stopColor="#0B0B0A" stopOpacity="0" />
          </radialGradient>

          {/* Golden 3D body gradient */}
          <linearGradient id="mascotGoldBody" x1="20%" y1="0%" x2="80%" y2="100%">
            <stop offset="0%" stopColor="#FFF2B2" />
            <stop offset="25%" stopColor="#F3CD64" />
            <stop offset="65%" stopColor="#D6A936" />
            <stop offset="100%" stopColor="#A47B16" />
          </linearGradient>

          {/* Golden Glow Filter */}
          <filter id="goldGlowFilter" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Sparkle Glow */}
          <filter id="sparkleGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Outer subtle golden aura nebula */}
        <ellipse cx="150" cy="100" rx="90" ry="55" fill="url(#mascotAura)" />

        {/* Orbit Ring 1 - Outer Tilted Ellipse */}
        <ellipse
          cx="150"
          cy="100"
          rx="125"
          ry="44"
          fill="none"
          stroke="rgba(214, 169, 54, 0.18)"
          strokeWidth="1"
          strokeDasharray="2 5"
        />

        {/* Orbit Ring 2 - Inner Tilted Ellipse */}
        <ellipse
          cx="150"
          cy="100"
          rx="105"
          ry="36"
          fill="none"
          stroke="rgba(214, 169, 54, 0.12)"
          strokeWidth="1"
        />

        {/* 4-Point Sparkle Stars along orbits */}
        {/* Star 1: Top-Left */}
        <path
          d="M 62 70 Q 64 74 68 74 Q 64 74 62 78 Q 60 74 56 74 Q 60 74 62 70 Z"
          fill="#FDE68A"
          filter="url(#sparkleGlow)"
        />
        {/* Star 2: Top-Right faint dot */}
        <circle cx="238" cy="72" r="1.5" fill="#D6A936" opacity="0.8" />
        {/* Star 3: Far Top-Right sparkle */}
        <path
          d="M 226 58 Q 227 60 229 60 Q 227 60 226 62 Q 225 60 223 60 Q 225 60 226 58 Z"
          fill="#D6A936"
          opacity="0.9"
        />
        {/* Star 4: Mid-Left lower sparkle */}
        <path
          d="M 50 128 Q 51.5 131 54 131 Q 51.5 131 50 134 Q 48.5 131 46 131 Q 48.5 131 50 128 Z"
          fill="#FDE68A"
          opacity="0.9"
          filter="url(#sparkleGlow)"
        />
        {/* Star 5: Bottom-Right sparkle */}
        <path
          d="M 252 135 Q 253.5 137 256 137 Q 253.5 137 252 139 Q 250.5 137 248 137 Q 250.5 137 252 135 Z"
          fill="#FDE68A"
          filter="url(#sparkleGlow)"
        />
        {/* Tiny stars / dust */}
        <circle cx="92" cy="116" r="1.2" fill="#D6A936" opacity="0.6" />
        <circle cx="212" cy="85" r="1.2" fill="#D6A936" opacity="0.6" />
        <circle cx="80" cy="85" r="1" fill="#FFF2B2" opacity="0.7" />

        {/* Mascot Character Group */}
        <g id="mascot-figure">
          {/* Main Golden Glowing Body */}
          <path
            fill="url(#mascotGoldBody)"
            filter="url(#goldGlowFilter)"
            d="M 150 48
               C 178 48, 202 59, 214 78
               C 225 96, 230 117, 228 135
               C 228 152, 220 162, 210 159
               C 201 156, 194 148, 189 138
               C 177 143, 164 145, 150 145
               C 136 145, 123 143, 111 138
               C 106 148, 99 156, 90 159
               C 80 162, 72 152, 72 135
               C 70 117, 75 96, 86 78
               C 98 59, 122 48, 150 48
               Z"
          />

          {/* Soft Forehead Highlight Sheen */}
          <ellipse
            cx="122"
            cy="70"
            rx="23"
            ry="9"
            fill="#FFFFFF"
            opacity="0.25"
            transform="rotate(-15 122 70)"
          />

          {/* Face Elements: Eyes & Smile */}
          {/* Left Eye */}
          <ellipse
            cx="125"
            cy="98"
            rx="11.5"
            ry="14.5"
            fill="#080808"
            style={{
              transformOrigin: '125px 98px',
              transform: isBlinking ? 'scaleY(0.05)' : 'scaleY(1)',
              transition: 'transform 70ms ease-in-out',
            }}
          />

          {/* Right Eye */}
          <ellipse
            cx="175"
            cy="98"
            rx="11.5"
            ry="14.5"
            fill="#080808"
            style={{
              transformOrigin: '175px 98px',
              transform: isBlinking ? 'scaleY(0.05)' : 'scaleY(1)',
              transition: 'transform 70ms ease-in-out',
            }}
          />

          {/* Smile */}
          <path
            d="M 129 116
               C 135 133, 165 133, 171 116
               C 163 124, 137 124, 129 116
               Z"
            fill="#080808"
          />
        </g>
      </svg>
    </div>
  );
};

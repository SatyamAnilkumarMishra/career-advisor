'use client';

import React from 'react';
import { Mascot } from './Mascot';

export const HeroSection: React.FC = () => {
  return (
    <section className="hero-section">
      <div className="hero-mascot-wrapper">
        <Mascot size={200} />
      </div>

      <div className="hero-text-block">
        <h2 className="hero-main-title">
          Hello! I’m <span className="hero-accent-gold">CareerAI</span>
        </h2>
        <p className="hero-subtitle-line">Your personal career companion.</p>
        <p className="hero-subtitle-line">How can I help you grow today?</p>
      </div>
    </section>
  );
};

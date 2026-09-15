import React from 'react';

interface CareerAiMarkProps {
  /** Rendered width in px. Height follows the 200:155 viewBox ratio. */
  size?: number;
  className?: string;
}

/**
 * The CareerAI mascot reduced to a flat mark, for use at text size.
 *
 * Shares the dock mascot's silhouette so the chat identity and the character
 * above the tab bar read as the same thing. Deliberately simplified for small
 * sizes: no glow filter, no gradient stops that would muddy at 16px, and the
 * smile stays a hole punched with `fillRule="evenodd"` so it reads against
 * whatever the bubble background happens to be.
 */
export const CareerAiMark: React.FC<CareerAiMarkProps> = ({ size = 16, className }) => (
  <svg
    width={size}
    height={size * (155 / 200)}
    viewBox="0 0 200 155"
    className={className}
    role="img"
    aria-label="CareerAI"
    focusable="false"
  >
    <path
      fillRule="evenodd"
      fill="currentColor"
      d="M 100 18
         C 132 18, 158 30, 172 52
         C 184 72, 190 96, 188 116
         C 188 136, 179 148, 167 144
         C 157 141, 149 132, 143 121
         C 130 127, 116 129, 100 129
         C 84 129, 70 127, 57 121
         C 51 132, 43 141, 33 144
         C 21 148, 12 136, 12 116
         C 10 96, 16 72, 28 52
         C 42 30, 68 18, 100 18
         Z
         M 60 95
         C 68 122, 132 122, 140 95
         C 132 110, 68 110, 60 95
         Z"
    />
    {/* Eyes are painted in the bubble's own background colour rather than
        punched out, so they stay dark on the light mark. */}
    <ellipse cx="72" cy="72" rx="15" ry="19" fill="var(--bubble-bg, #161230)" />
    <ellipse cx="128" cy="72" rx="15" ry="19" fill="var(--bubble-bg, #161230)" />
  </svg>
);

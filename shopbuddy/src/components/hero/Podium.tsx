'use client';

import React, { useId } from 'react';

interface PodiumProps {
  className?: string;
}

export const Podium: React.FC<PodiumProps> = ({ className }) => {
  const gradientId = useId();

  return (
    <svg
      viewBox="0 0 400 200"
      width="100%"
      height="100%"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#ebe6d6" />
          <stop offset="35%" stopColor="#f7f4ea" />
          <stop offset="100%" stopColor="#e6e1d0" />
        </linearGradient>
      </defs>

      {/* Body: path from (10,60) down to (10,150), curving along bottom ellipse (rx 190, ry 40) to (390,150), up to (390,60) */}
      <path
        d="M 10 60 L 10 150 A 190 40 0 0 0 390 150 L 390 60 Z"
        fill={`url(#${gradientId})`}
      />

      {/* Top face: ellipse cx 200 cy 60 rx 190 ry 40, fill #f9f7ee, stroke none */}
      <ellipse
        cx="200"
        cy="60"
        rx="190"
        ry="40"
        fill="#f9f7ee"
        stroke="none"
      />

      {/* Subtle inner top-edge highlight: ellipse rx 186 ry 36, fill none, stroke #ffffff, stroke-opacity .7, stroke-width 2 */}
      <ellipse
        cx="200"
        cy="60"
        rx="186"
        ry="36"
        fill="none"
        stroke="#ffffff"
        strokeOpacity="0.7"
        strokeWidth="2"
      />
    </svg>
  );
};

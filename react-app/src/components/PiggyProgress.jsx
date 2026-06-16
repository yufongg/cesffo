import React from 'react';

// Coin positions [cx, cy] stacked from the bottom of the piggy upward. The whole
// stack is clipped to the body and slides up as progress increases, so the piggy
// visually "fills with coins".
const COINS = [
  [50, 90], [78, 90],
  [42, 84], [64, 84], [86, 84],
  [50, 78], [72, 78],
  [40, 72], [62, 72], [84, 72],
  [50, 66], [72, 66],
  [44, 60], [66, 60], [88, 60],
  [52, 54], [74, 54],
  [46, 48], [68, 48],
  [58, 42],
];

export default function PiggyProgress({ pct = 0, level }) {
  const frac = Math.max(0, Math.min(1, (pct || 0) / 100));
  const offset = (1 - frac) * 80; // coins sit below the body when empty

  return (
    <div
      className="piggy"
      role="img"
      aria-label={`Savings progress ${Math.round(pct)} percent`}
    >
      <svg className="piggy__svg" viewBox="0 0 132 120">
        <defs>
          <clipPath id="piggyBody">
            <ellipse cx="64" cy="60" rx="48" ry="36" />
          </clipPath>
          <linearGradient id="piggyCoin" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#f3dd84" />
            <stop offset="1" stopColor="#c19a36" />
          </linearGradient>
        </defs>

        {/* empty (transparent) vessel */}
        <ellipse cx="64" cy="60" rx="48" ry="36" className="piggy__fillbg" />

        {/* rising coins */}
        <g clipPath="url(#piggyBody)">
          <g className="piggy__coins" style={{ transform: `translateY(${offset}px)` }}>
            {COINS.map(([cx, cy], i) => (
              <ellipse key={i} cx={cx} cy={cy} rx="13" ry="4.3" className="piggy__coin" />
            ))}
          </g>
        </g>

        {/* body + features — outline only, so the piggy reads as transparent glass */}
        <g className="piggy__outline">
          <ellipse cx="64" cy="60" rx="48" ry="36" />
          <path d="M94 32 L108 26 L105 43 Z" />               {/* ear */}
          <ellipse cx="108" cy="64" rx="11" ry="10" />        {/* snout */}
          <rect x="40" y="90" width="11" height="16" rx="4" />{/* leg */}
          <rect x="78" y="90" width="11" height="16" rx="4" />{/* leg */}
        </g>

        {/* coin slot, nostrils, eye */}
        <rect x="54" y="24" width="22" height="5" rx="2.5" className="piggy__ink" />
        <circle cx="105" cy="64" r="1.6" className="piggy__ink" />
        <circle cx="111" cy="64" r="1.6" className="piggy__ink" />
        <circle cx="82" cy="50" r="2.6" className="piggy__ink" />
      </svg>

      {Number.isFinite(level) && <span className="piggy__level">Level {level}</span>}
    </div>
  );
}

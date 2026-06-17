import React from 'react';

// Category selector rendered as filter chips, matching the Marketplace styling.
export default function ForumCategoryNav({ categories, selectedCategoryId, onSelect }) {
  if (!categories.length) return null;

  return (
    <div className="chips" role="group" aria-label="Forum categories">
      {categories.map((category) => (
        <button
          key={category.category_id}
          type="button"
          className={`chip ${category.category_id === selectedCategoryId ? 'chip--active' : ''}`}
          onClick={() => onSelect(category)}
        >
          {category.name}
        </button>
      ))}
    </div>
  );
}

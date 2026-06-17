function CategoryList({ categories, selectedCategoryId, onSelectCategory }) {
  function handleChange(event) {
    const category = categories.find((item) => item.category_id === event.target.value);
    if (category) onSelectCategory(category);
  }

  return (
    <section className="category-filter-card">
      <div className="category-filter-main">
        <div>
          <h1>Course Discussion Board</h1>
          <p className="muted">Browse course discussion topics, view posts, create posts, attach images, and receive live updates.</p>
        </div>

        <label className="category-select-label">
          <span>Category</span>
          <select value={selectedCategoryId || ''} onChange={handleChange}>
            {categories.map((category) => (
              <option value={category.category_id} key={category.category_id}>{category.name}</option>
            ))}
          </select>
        </label>
      </div>
    </section>
  );
}

export default CategoryList;

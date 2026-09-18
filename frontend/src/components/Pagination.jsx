export default function Pagination({ skip, limit, total, onPageChange }) {
  const currentPage = Math.floor(skip / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  if (totalPages <= 1) return null;

  const goTo = (page) => {
    const clamped = Math.max(1, Math.min(page, totalPages));
    onPageChange((clamped - 1) * limit);
  };

  return (
    <div className="pagination">
      <button
        disabled={currentPage === 1}
        onClick={() => goTo(currentPage - 1)}
      >
        ‹ Prev
      </button>
      <span className="page-indicator">
        Page {currentPage} of {totalPages} · {total} total
      </span>
      <button
        disabled={currentPage === totalPages}
        onClick={() => goTo(currentPage + 1)}
      >
        Next ›
      </button>
    </div>
  );
}

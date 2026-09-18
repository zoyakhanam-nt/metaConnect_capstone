import { useEffect } from "react";

export default function Toast({ message, type = "info", onDismiss }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onDismiss, 4000);
    return () => clearTimeout(t);
  }, [message, onDismiss]);

  if (!message) return null;

  return (
    <div className={`toast toast-${type}`}>
      {message}
      <button className="toast-close" onClick={onDismiss}>
        ×
      </button>
    </div>
  );
}

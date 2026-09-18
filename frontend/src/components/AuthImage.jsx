import { useEffect, useState } from "react";
import { getToken } from "../auth.js";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export default function AuthImage({ path, alt }) {
  const [src, setSrc] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let objectUrl;
    fetch(`${BASE_URL}${path}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load chart");
        return res.blob();
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch((e) => setError(e.message));

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  if (error) return <p className="error">{error}</p>;
  if (!src) return <p>Loading chart...</p>;
  return <img src={src} alt={alt} className="chart-img" />;
}

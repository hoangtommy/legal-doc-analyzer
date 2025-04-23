import React, { useState } from "react";

function FileUpload() {
  const [files, setFiles] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
    setResult(null);
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!files.length) return;
    setLoading(true);
    setResult(null);
    setError("");
    const formData = new FormData();
    files.forEach((file, idx) => {
      formData.append("files", file);
    });
    try {
      const response = await fetch("https://legal-doc-analyzer.onrender.com/upload", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (data.result) {
        setResult(data.result);
      } else {
        setError(data.error || "Unknown error");
      }
    } catch (err) {
      setError("Failed to connect to backend.");
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 600, margin: "2rem auto", padding: 24, background: "#f4f6fa", borderRadius: 12 }}>
      <h2>Legal Document Analyzer</h2>
      <form onSubmit={handleSubmit} style={{ marginBottom: 24 }}>
        <input
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={handleFileChange}
          style={{ marginBottom: 12 }}
        />
        <br />
        <button type="submit" disabled={loading || !files.length} style={{ marginTop: 8 }}>
          {loading ? "Analyzing..." : "Upload & Analyze"}
        </button>
      </form>
      {result && (
        <pre style={{ textAlign: "left", background: "#eee", padding: 16, borderRadius: 8 }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
      {error && <div style={{ color: "#d32f2f", marginBottom: 16 }}>{error}</div>}
    </div>
  );
}

export default FileUpload;

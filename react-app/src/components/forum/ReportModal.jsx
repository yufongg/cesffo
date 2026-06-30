import React, { useState } from "react";

const REPORT_REASONS = [
  "Spam",
  "Harassment",
  "False information",
  "Offensive content",
  "Scam / Fraud",
  "Other",
];

export default function ReportModal({
  open,
  type = "thread",
  onClose,
  onSubmit,
}) {
  const [reason, setReason] = useState("Spam");
  const [description, setDescription] = useState("");

  if (!open) return null;

  async function handleSubmit(e) {
    e.preventDefault();

    await onSubmit(reason, description);

    setReason("Spam");
    setDescription("");
  }

  return (
    <div className="report-modal-overlay">
      <div className="report-modal">

        <div className="report-modal-header">
          <h2>
            Report {type === "thread" ? "Thread" : "Reply"}
          </h2>

          <button
            type="button"
            className="report-close"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit}>

          <label>
            Reason
          </label>

          <select
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          >
            {REPORT_REASONS.map((item) => (
              <option key={item}>
                {item}
              </option>
            ))}
          </select>

          <label>
            Additional details (optional)
          </label>

          <textarea
            rows="5"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Tell us more about why you're reporting this content..."
          />

          <div className="report-modal-actions">

            <button
              type="button"
              className="btn btn--secondary"
              onClick={onClose}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="btn btn--danger"
            >
              Submit Report
            </button>

          </div>

        </form>

      </div>
    </div>
  );
}
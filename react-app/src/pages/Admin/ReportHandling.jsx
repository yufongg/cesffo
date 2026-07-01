import { useEffect, useState } from "react";
import { listAdminReports } from "../../services/forumApi";

export default function ReportHandling() {
  const [reports, setReports] = useState([]);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    loadReports();
  }, []);

  async function loadReports() {
    try {
      const data = await listAdminReports();
      setReports(data);
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <span className="eyebrow">Admin</span>
          <h1>Report Handling</h1>
          <p className="subtitle">
            Review and moderate reports submitted by users.
          </p>
        </div>

        <div className="report-admin-list">
          {reports.map((group) => {
            const reasonSummary = {};
            const status = group.reports[0]?.status || "Pending";
            const uniqueId = group.thread_id || group.post_id;

            group.reports.forEach((r) => {
              reasonSummary[r.reason] = (reasonSummary[r.reason] || 0) + 1;
            });

            return (
              <div key={uniqueId} className="card report-admin-card">
                <div className="card__body">
                  <div className="report-admin-header">
                    <div>
                      <span className="report-type">
                        {group.type === "Thread" ? "Thread" : "Reply"}
                      </span>
                      <h3>{group.title}</h3>
                    </div>

                    <div className="report-badges">
                      <span className={`report-status status-${status.toLowerCase()}`}>
                        {status}
                      </span>
                      <span className="report-count">
                        {group.report_count} Report
                        {group.report_count > 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>

                  <div className="report-section">
                    <label>Reports Summary</label>
                    <ul className="report-summary-list">
                      {Object.entries(reasonSummary).map(([reason, count]) => (
                        <li key={reason}>
                          <span>{reason}</span>
                          <span className="reason-count">{count}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="report-section">
                    <label>Reported Content</label>
                    <p className="reported-content">{group.reported_content}</p>
                  </div>

                  <div className="report-actions">
                    <button
                      className="btn btn--secondary btn--sm"
                      onClick={() =>
                        setExpanded(expanded === uniqueId ? null : uniqueId)
                      }
                    >
                      {expanded === uniqueId ? "Hide Reports" : "View Reports"}
                    </button>
                  </div>

                  {expanded === uniqueId && (
                    <div className="report-details">
                      {group.reports.map((r) => (
                        <div key={r.report_id} className="report-detail-card">
                          <div className="report-detail-header">
                            <strong>👤 {r.reporter_name}</strong>
                            <small>
                              {new Date(r.created_at).toLocaleString()}
                            </small>
                          </div>
                          <p>
                            <strong>Reason:</strong> {r.reason}
                          </p>
                          <p>
                            <strong>Description:</strong> {r.description || "-"}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="report-footer">
                    <div className="row-actions">
                      <button className="btn btn--secondary btn--sm">Reject</button>
                      <button className="btn btn--secondary btn--sm">Resolve</button>
                      <button className="btn btn--danger btn--sm">Remove Content</button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
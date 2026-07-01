export default function MyReportsPanel({ reports }) {

    return (
        <section className="report-panel">

            {reports.length === 0 ? (

                <div className="empty-state">
                    <h3>No reports submitted</h3>

                    <p>
                        Reports you submit will appear here.
                    </p>
                </div>

            ) : (

                reports.map(report => (

                    <div
                        key={report.report_id}
                        className="report-card"
                    >

                        <h3>{report.title}</h3>

                        <p>
                            <strong>Reported Content</strong>
                        </p>

                        <p>
                            {report.reported_content}
                        </p>

                        <p>
                            <strong>Reason</strong>
                        </p>

                        <p>
                            {report.reason}
                        </p>

                        {report.description && (
                            <>
                                <p>
                                    <strong>Your Description</strong>
                                </p>

                                <p>
                                    {report.description}
                                </p>
                            </>
                        )}

                        <p>
                            <strong>Status:</strong> {report.status}
                        </p>

                        <small>
                            {new Date(report.created_at).toLocaleString()}
                        </small>

                    </div>

                ))

            )}

        </section>
    );

}
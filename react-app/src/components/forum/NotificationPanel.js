import { formatDate } from '../../utils/forumText';

function NotificationPanel({ notifications, userId, onMarkRead }) {
  const unreadCount = notifications.filter((notification) => !notification.is_read).length;

  return (
    <aside className="card notification-card">
      <h2>Notifications <span>{unreadCount}</span></h2>
      {!userId && <p className="muted">Set a user ID to receive notifications.</p>}
      {notifications.map((notification) => (
        <div className={`notification ${notification.is_read ? '' : 'unread'}`} key={notification.notification_id}>
          <p>{notification.message}</p>
          <small>{formatDate(notification.created_at)}</small>
          {!notification.is_read && (
            <button type="button" onClick={() => onMarkRead(notification.notification_id)}>Mark read</button>
          )}
        </div>
      ))}
    </aside>
  );
}

export default NotificationPanel;

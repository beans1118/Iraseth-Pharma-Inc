
const API_BASE = "http://localhost:5000/api";
// Same host as API_BASE, without the /api suffix — used for the Socket.IO
// connection that pushes real-time inventory/log updates to the admin console.
const SOCKET_BASE = API_BASE.replace(/\/api\/?$/, "");

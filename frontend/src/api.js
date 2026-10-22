const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", token, json, form } = {}) {
  const headers = {};
  let body;
  if (token) headers.Authorization = `Bearer ${token}`;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }
  if (form) body = new URLSearchParams(form);

  const res = await fetch(`${BASE}${path}`, { method, headers, body });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const data = await res.json();
      if (Array.isArray(data.detail)) message = data.detail.map((d) => d.msg).join(", ");
      else if (typeof data.detail === "string") message = data.detail;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(res.status, message);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  register: (data) => request("/auth/register", { method: "POST", json: data }),
  login: (email, password) =>
    request("/auth/login", { method: "POST", form: { username: email, password } }),

  listTrips: (token) => request("/trips", { token }),
  createTrip: (token, data) => request("/trips", { method: "POST", token, json: data }),
  markSafe: (token, id) => request(`/trips/${id}/safe`, { method: "POST", token }),
  extendTrip: (token, id, deadline) =>
    request(`/trips/${id}/extend`, { method: "POST", token, json: { deadline } }),
  deleteTrip: (token, id) => request(`/trips/${id}`, { method: "DELETE", token }),
  tripDeliveries: (token, id) => request(`/trips/${id}/deliveries`, { token }),

  listBuddies: (token) => request("/buddies", { token }),
  addBuddy: (token, name, email) =>
    request("/buddies", { method: "POST", token, json: { name, email } }),
  resendBuddy: (token, id) => request(`/buddies/${id}/resend`, { method: "POST", token }),
  removeBuddy: (token, id) => request(`/buddies/${id}`, { method: "DELETE", token }),
  confirmBuddy: (confirmToken) =>
    request("/buddies/confirm", { method: "POST", json: { token: confirmToken } }),

  getWatch: (token) => request(`/watch/${token}`),
  ackWatch: (token) => request(`/watch/${token}/ack`, { method: "POST" }),
};
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

const getHeaders = () => {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
};

const handleResponse = async (response) => {
  if (!response.ok) {
    let errorMsg = "Something went wrong";
    try {
      const data = await response.json();
      errorMsg = data.detail || errorMsg;
    } catch (e) {}
    throw new Error(errorMsg);
  }
  return response.json();
};

export const api = {
  // Auth
  register: async (email, password, name) => {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ email, password, name }),
    });
    return handleResponse(res);
  },

  login: async (email, password) => {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ email, password }),
    });
    const data = await handleResponse(res);
    localStorage.setItem("token", data.access_token);
    return data;
  },

  me: async () => {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      method: "GET",
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  logout: () => {
    localStorage.removeItem("token");
  },

  // Groups
  listGroups: async () => {
    const res = await fetch(`${API_BASE_URL}/groups`, {
      method: "GET",
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  createGroup: async (name, description) => {
    const res = await fetch(`${API_BASE_URL}/groups`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ name, description }),
    });
    return handleResponse(res);
  },

  getGroup: async (groupId) => {
    const res = await fetch(`${API_BASE_URL}/groups/${groupId}`, {
      method: "GET",
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  addMember: async (groupId, email) => {
    const res = await fetch(`${API_BASE_URL}/groups/${groupId}/members`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ email }),
    });
    return handleResponse(res);
  },

  removeMember: async (groupId, userId) => {
    const res = await fetch(`${API_BASE_URL}/groups/${groupId}/members/${userId}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  // Expenses
  listExpenses: async (groupId) => {
    const res = await fetch(`${API_BASE_URL}/groups/${groupId}/expenses`, {
      method: "GET",
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  createExpense: async (groupId, expenseData) => {
    const res = await fetch(`${API_BASE_URL}/groups/${groupId}/expenses`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(expenseData),
    });
    return handleResponse(res);
  },

  // Settlements
  listSettlements: async (groupId) => {
    const res = await fetch(`${API_BASE_URL}/groups/${groupId}/settlements`, {
      method: "GET",
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  createSettlement: async (groupId, settlementData) => {
    const res = await fetch(`${API_BASE_URL}/groups/${groupId}/settlements`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify(settlementData),
    });
    return handleResponse(res);
  },

  // Balances
  getBalances: async (groupId) => {
    const res = await fetch(`${API_BASE_URL}/groups/${groupId}/balances`, {
      method: "GET",
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  // Imports
  uploadCSV: async (groupId, file) => {
    const formData = new FormData();
    formData.append("file", file);

    const token = localStorage.getItem("token");
    const headers = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE_URL}/groups/${groupId}/imports/upload`, {
      method: "POST",
      headers: headers, // fetch automatically sets multipart headers for FormData
      body: formData,
    });
    return handleResponse(res);
  },

  getImportDetails: async (importId) => {
    const res = await fetch(`${API_BASE_URL}/imports/${importId}`, {
      method: "GET",
      headers: getHeaders(),
    });
    return handleResponse(res);
  },

  approveImport: async (importId, resolutions) => {
    const res = await fetch(`${API_BASE_URL}/imports/${importId}/approve`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ resolutions }),
    });
    return handleResponse(res);
  },
};

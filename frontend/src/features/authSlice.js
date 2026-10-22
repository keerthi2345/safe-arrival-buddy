import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api } from "../api";

export const AUTH_KEY = "sab_auth";

function loadSaved() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_KEY)) || {};
  } catch {
    return {};
  }
}

export const login = createAsyncThunk(
  "auth/login",
  async ({ email, password }, { rejectWithValue }) => {
    try {
      const data = await api.login(email, password);
      return { token: data.access_token, email };
    } catch (e) {
      return rejectWithValue(e.message);
    }
  }
);

export const register = createAsyncThunk(
  "auth/register",
  async ({ email, name, password }, { rejectWithValue }) => {
    try {
      await api.register({ email, name, password });
      const data = await api.login(email, password);
      return { token: data.access_token, email };
    } catch (e) {
      return rejectWithValue(e.message);
    }
  }
);

const saved = loadSaved();

const authSlice = createSlice({
  name: "auth",
  initialState: {
    token: saved.token || null,
    email: saved.email || null,
    status: "idle",
    error: null,
  },
  reducers: {
    logout(state) {
      state.token = null;
      state.email = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    for (const thunk of [login, register]) {
      builder
        .addCase(thunk.pending, (state) => {
          state.status = "loading";
          state.error = null;
        })
        .addCase(thunk.fulfilled, (state, action) => {
          state.status = "idle";
          state.token = action.payload.token;
          state.email = action.payload.email;
        })
        .addCase(thunk.rejected, (state, action) => {
          state.status = "idle";
          state.error = action.payload || "Something went wrong";
        });
    }
  },
});

export const { logout } = authSlice.actions;
export default authSlice.reducer;
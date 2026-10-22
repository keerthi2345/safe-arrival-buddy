import { configureStore } from "@reduxjs/toolkit";
import authReducer, { AUTH_KEY } from "./features/authSlice";
import tripsReducer from "./features/tripsSlice";

export const store = configureStore({
  reducer: { auth: authReducer, trips: tripsReducer },
});

// Keep the login across page reloads
store.subscribe(() => {
  const { token, email } = store.getState().auth;
  if (token) localStorage.setItem(AUTH_KEY, JSON.stringify({ token, email }));
  else localStorage.removeItem(AUTH_KEY);
});
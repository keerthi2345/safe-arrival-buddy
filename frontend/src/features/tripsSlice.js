import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api } from "../api";
import { logout } from "./authSlice";

// Every call uses the saved token; an expired token (401) logs the user out.
function guarded(type, call) {
  return createAsyncThunk(type, async (arg, { getState, dispatch, rejectWithValue }) => {
    try {
      return await call(getState().auth.token, arg);
    } catch (e) {
      if (e.status === 401) dispatch(logout());
      return rejectWithValue(e.message);
    }
  });
}

export const fetchTrips = guarded("trips/fetch", (token) => api.listTrips(token));
export const createTrip = guarded("trips/create", (token, data) => api.createTrip(token, data));
export const markSafe = guarded("trips/safe", (token, id) => api.markSafe(token, id));
export const extendTrip = guarded("trips/extend", (token, { id, deadline }) =>
  api.extendTrip(token, id, deadline)
);

const initialState = { items: [], status: "idle", error: null };

function upsert(state, trip) {
  const index = state.items.findIndex((t) => t.id === trip.id);
  if (index === -1) state.items.unshift(trip);
  else state.items[index] = trip;
}

const tripsSlice = createSlice({
  name: "trips",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchTrips.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchTrips.fulfilled, (state, action) => {
        state.status = "idle";
        state.items = action.payload;
        state.error = null;
      })
      .addCase(fetchTrips.rejected, (state, action) => {
        state.status = "idle";
        state.error = action.payload || "Could not load trips";
      })
      .addCase(createTrip.fulfilled, (state, action) => upsert(state, action.payload))
      .addCase(markSafe.fulfilled, (state, action) => upsert(state, action.payload))
      .addCase(extendTrip.fulfilled, (state, action) => upsert(state, action.payload))
      .addCase(logout, () => initialState);
  },
});

export default tripsSlice.reducer;
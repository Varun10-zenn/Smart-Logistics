# Smart Logistics Platform — Manual Module Testing Guide

This guide provides step-by-step instructions for manually testing every domain module using the web interface (`http://localhost:5173`) and API endpoints (`http://localhost:8000/api/v1`).

---

## 1. Authentication Testing
1. Navigate to `http://localhost:5173/login`.
2. Enter Credentials:
   - **Username**: `admin`
   - **Password**: `admin123`
3. Click **Sign In**.
4. **Expected Result**: Redirected to `/dashboard`. Auth token is stored in browser `localStorage.getItem('token')`.

---

## 2. Warehouse Module Testing (`/warehouse`)
1. Navigate to `http://localhost:5173/warehouse`.
2. **View Dark-Store Canvas**: Select a warehouse from the dropdown (e.g., Warehouse 1). Observe nodes and storage locations rendered on the interactive SVG canvas.
3. **Inspect Pending Orders**: Observe the list of pending pick orders in the sidebar.
4. **Run Batch Optimization**:
   - Click **Run Batch Optimization**.
   - Input constraints (or keep defaults: Max 5 orders, 150 kg).
   - Click **Execute Optimization**.
5. **Verify API Call**:
   - DevTools $\rightarrow$ Network Tab: `POST /api/v1/batches/optimize` returning `HTTP 200 OK`.
6. **Verify Database**:
   - Execute MySQL Query:
     ```sql
     SELECT * FROM batches ORDER BY id DESC LIMIT 1;
     SELECT * FROM pick_routes ORDER BY id DESC LIMIT 1;
     ```
   - Confirm status of batched orders changed from `pending` to `batched`.

---

## 3. Delivery Module Testing (`/deliveries`)
1. Navigate to `http://localhost:5173/deliveries`.
2. **Create Delivery**: Click **New Delivery**, select an order, driver, and vehicle, then click **Create**.
3. **Generate Route**: Click on the newly created delivery to open `http://localhost:5173/deliveries/{id}`, then click **Generate Route**.
4. **Verify API & DB**:
   - Network call: `POST /api/v1/deliveries/{id}/route`.
   - MySQL check: `SELECT status, estimated_eta FROM deliveries WHERE id = {id};`.

---

## 4. Safety Module Testing (`/safety`)
1. Navigate to `http://localhost:5173/safety`.
2. **Inspect Dashboard**: View Safety Scores, recent Safety Events, and active Safety Alerts.
3. **Telemetry Testing Notice**:
   > [!NOTE]
   > The React frontend does NOT contain a manual form for submitting raw GPS telemetry. Telemetry must be submitted via backend API or Swagger UI (`http://localhost:8000/docs`).
4. **API Telemetry Submission**:
   - Send HTTP `POST http://localhost:8000/api/v1/telemetry` with payload:
     ```json
     {
       "delivery_id": 1,
       "timestamp": "2026-10-02T12:00:00Z",
       "latitude": 12.9716,
       "longitude": 77.5946,
       "speed_kmh": 95.0,
       "acceleration_mpss": -4.5
     }
     ```
5. **Verify Safety Output**: Refresh `/safety` to observe newly generated speeding/harsh braking events and score deduction.

---

## 5. EV Charging Module Testing (`/charging`)
1. Navigate to `http://localhost:5173/charging`.
2. **View Stations**: Observe charging stations on map and grid.
3. **Generate Recommendation**: Go to `/charging/optimize`, select vehicle SoC (e.g., 15%), and click **Find Best Charging Station**.
4. **Reserve Slot**: Select a recommended slot and click **Confirm Reservation**.
5. **Verify Database**:
   - Query: `SELECT * FROM charging_reservations ORDER BY id DESC LIMIT 1;`
   - Check that `charging_slots.is_booked` is set to `1` for the reserved slot.

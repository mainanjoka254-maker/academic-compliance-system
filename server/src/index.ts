import "dotenv/config";
import cookieParser from "cookie-parser";
import cors from "cors";
import express from "express";
import helmet from "helmet";
import { env } from "./config/env.js";
import { errorHandler } from "./middleware/error.js";
import { academicRouter } from "./routes/academic.js";
import { aiRouter, complianceRouter } from "./routes/compliance.js";
import { authRouter } from "./routes/auth.js";
import { orgRouter } from "./routes/org.js";
import { studentsRouter } from "./routes/students.js";
import { usersRouter } from "./routes/users.js";
import { accountRouter } from "./routes/account.js";

const app = express();

app.use(helmet());
app.use(cors({ origin: env.clientOrigin, credentials: true }));
app.use(express.json({ limit: "2mb" }));
app.use(cookieParser());

app.get("/health", (_req, res) => res.json({ status: "ok", service: "academic-compliance" }));
app.use("/api/auth", authRouter);
app.use("/api/org", orgRouter);
app.use("/api/academic", academicRouter);
app.use("/api/students", studentsRouter);
app.use("/api/users", usersRouter);
app.use("/api/account", accountRouter);
app.use("/api/compliance", complianceRouter);
app.use("/api/ai", aiRouter);
app.use(errorHandler);

app.listen(env.port, () => {
  console.log(`Academic Compliance API listening on port ${env.port}`);
});

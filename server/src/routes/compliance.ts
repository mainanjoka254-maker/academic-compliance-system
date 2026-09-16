import { Router } from "express";
import { z } from "zod";
import { prisma } from "../lib/prisma.js";
import { asyncHandler } from "../utils/asyncHandler.js";
import { authenticate, authorize } from "../middleware/auth.js";
import { writeAudit } from "../middleware/audit.js";
import { HttpError } from "../utils/httpError.js";
import { analyzeStudent } from "../services/ai/analyzer.js";
import { recomputeAll, recomputeStudentCompliance } from "../services/compliance/engine.js";

export const complianceRouter = Router();
complianceRouter.use(authenticate);

complianceRouter.get(
  "/rules",
  authorize("ADMIN", "ACADEMIC_OFFICER"),
  asyncHandler(async (_req, res) => {
    res.json({ rules: await prisma.complianceRule.findMany({ orderBy: { key: "asc" } }) });
  }),
);

complianceRouter.patch(
  "/rules/:id",
  authorize("ADMIN"),
  asyncHandler(async (req, res) => {
    const data = z
      .object({
        enabled: z.boolean().optional(),
        threshold: z.number().optional(),
        name: z.string().optional(),
        description: z.string().optional(),
        config: z.record(z.string(), z.unknown()).optional(),
      })
      .parse(req.body);
    const rule = await prisma.complianceRule.update({ where: { id: String(req.params.id) }, data: { ...data, config: data.config as object | undefined } });
    await writeAudit({ req, action: "COMPLIANCE_RULE_CHANGED", entity: "ComplianceRule", entityId: rule.id });
    res.json({ rule });
  }),
);

complianceRouter.get(
  "/records",
  authorize("ADMIN", "ACADEMIC_OFFICER", "LECTURER"),
  asyncHandler(async (req, res) => {
    const records = await prisma.complianceRecord.findMany({
      include: {
        student: { include: { user: true, program: true } },
        semester: true,
      },
      orderBy: { computedAt: "desc" },
      take: 300,
    });
    res.json({ records });
  }),
);

complianceRouter.post(
  "/recompute",
  authorize("ADMIN", "ACADEMIC_OFFICER"),
  asyncHandler(async (req, res) => {
    const { studentId } = z.object({ studentId: z.string().optional() }).parse(req.body ?? {});
    if (studentId) {
      const result = await recomputeStudentCompliance(studentId);
      await writeAudit({ req, action: "AI_RECOMMENDATION_GENERATED", entity: "Student", entityId: studentId });
      return res.json(result);
    }
    const count = await recomputeAll();
    await writeAudit({ req, action: "AI_RECOMMENDATION_GENERATED", entity: "ComplianceRecord", metadata: { count } });
    res.json({ recomputed: count });
  }),
);

complianceRouter.patch(
  "/records/:id/review",
  authorize("ADMIN", "ACADEMIC_OFFICER"),
  asyncHandler(async (req, res) => {
    const data = z
      .object({
        reviewStatus: z.enum(["PENDING", "APPROVED", "FLAGGED"]),
        reviewNote: z.string().optional(),
      })
      .parse(req.body);
    const record = await prisma.complianceRecord.update({
      where: { id: String(req.params.id) },
      data: { reviewStatus: data.reviewStatus, reviewNote: data.reviewNote, reviewedById: req.user!.id },
    });
    await writeAudit({ req, action: "COMPLIANCE_REVIEWED", entity: "ComplianceRecord", entityId: record.id });
    res.json({ record });
  }),
);

complianceRouter.patch(
  "/recommendations/:id/override",
  authorize("ADMIN", "ACADEMIC_OFFICER", "LECTURER"),
  asyncHandler(async (req, res) => {
    const data = z
      .object({
        overrideRisk: z.enum(["LOW", "MEDIUM", "HIGH"]),
        overrideNote: z.string().min(3),
      })
      .parse(req.body);
    const rec = await prisma.aiRecommendation.update({
      where: { id: String(req.params.id) },
      data: {
        overridden: true,
        reviewedById: req.user!.id,
        overrideRisk: data.overrideRisk,
        overrideNote: data.overrideNote,
      },
    });
    await writeAudit({ req, action: "AI_OVERRIDE", entity: "AiRecommendation", entityId: rec.id });
    res.json({ recommendation: rec });
  }),
);

complianceRouter.get(
  "/alerts",
  asyncHandler(async (req, res) => {
    if (req.user!.role === "STUDENT") {
      const alerts = await prisma.academicAlert.findMany({
        where: { studentId: req.user!.studentId, isRead: false },
        orderBy: { createdAt: "desc" },
      });
      return res.json({ alerts });
    }
    const alerts = await prisma.academicAlert.findMany({
      where: { isRead: false },
      include: { student: { include: { user: true } } },
      orderBy: { createdAt: "desc" },
      take: 200,
    });
    res.json({ alerts });
  }),
);

complianceRouter.post(
  "/alerts/:id/resolve",
  authorize("ADMIN", "ACADEMIC_OFFICER", "LECTURER"),
  asyncHandler(async (req, res) => {
    const alert = await prisma.academicAlert.update({ where: { id: String(req.params.id) }, data: { isRead: true } });
    res.json({ alert });
  }),
);

export const aiRouter = Router();
aiRouter.use(authenticate);

aiRouter.post(
  "/ask",
  asyncHandler(async (req, res) => {
    const { question } = z.object({ question: z.string().min(2).max(1000) }).parse(req.body);
    const normalized = question.toLowerCase();
    let answer =
      "I can help with attendance thresholds, GPA and CGPA, missing assessments, course registration, compliance status, risk levels, and academic support. Ask about one of those areas.";
    if (normalized.includes("attendance")) {
      answer = "Attendance is evaluated from recorded PRESENT, LATE, and EXCUSED sessions. The default minimum is 75%, but an administrator can adjust that rule.";
    } else if (normalized.includes("gpa") || normalized.includes("cgpa")) {
      answer = "GPA is calculated from graded courses in the selected semester, while CGPA uses all graded enrollments. A GPA below the configured minimum can place a student at risk.";
    } else if (normalized.includes("risk") || normalized.includes("non-compliant")) {
      answer = "Risk is advisory and evidence-based. High risk can be triggered by multiple serious violations, very low attendance, failed core courses, or GPA below the minimum. Review the underlying record before taking action.";
    } else if (normalized.includes("assessment") || normalized.includes("mark")) {
      answer = "Missing CAT, assignment, or exam marks are flagged as a compliance issue. Once marks are entered, the student's grade and compliance record can be recomputed.";
    } else if (normalized.includes("registration") || normalized.includes("credit")) {
      answer = "The system checks current-semester registration and compares registered credits with the configured minimum. Programme completion is based on earned credits against required programme credits.";
    }
    res.json({ answer, source: "local-academic-agent" });
  }),
);

aiRouter.post(
  "/analyze",
  authorize("ADMIN", "ACADEMIC_OFFICER", "LECTURER"),
  asyncHandler(async (req, res) => {
    const { studentId } = z.object({ studentId: z.string() }).parse(req.body);
    if (req.user!.role === "LECTURER" && req.user!.lecturerId) {
      const allowed = await prisma.enrollment.findFirst({
        where: { studentId, offering: { lecturerId: req.user!.lecturerId } },
      });
      if (!allowed) throw new HttpError(403, "Not assigned to this student");
    }
    await recomputeStudentCompliance(studentId);
    const result = await analyzeStudent(studentId, req.user!.id);
    await writeAudit({ req, action: "AI_RECOMMENDATION_GENERATED", entity: "Student", entityId: studentId });
    res.json(result);
  }),
);

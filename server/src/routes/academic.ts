import { Router } from "express";
import { z } from "zod";
import { prisma } from "../lib/prisma.js";
import { asyncHandler } from "../utils/asyncHandler.js";
import { authenticate, authorize } from "../middleware/auth.js";
import { HttpError } from "../utils/httpError.js";
import { writeAudit } from "../middleware/audit.js";
import { recomputeEnrollmentGrade } from "../services/grades.js";
import { recomputeStudentCompliance } from "../services/compliance/engine.js";

export const academicRouter = Router();
academicRouter.use(authenticate);

async function assertLecturerOffering(lecturerId: string | undefined, offeringId: string, role: string) {
  if (role === "ADMIN" || role === "ACADEMIC_OFFICER") return;
  const offering = await prisma.courseOffering.findUnique({ where: { id: offeringId } });
  if (!offering || offering.lecturerId !== lecturerId) throw new HttpError(403, "Not assigned to this course");
}

academicRouter.get(
  "/offerings",
  asyncHandler(async (req, res) => {
    const where =
      req.user!.role === "LECTURER" && req.user!.lecturerId ? { lecturerId: req.user!.lecturerId } : {};
    const offerings = await prisma.courseOffering.findMany({
      where,
      include: {
        course: true,
        semester: true,
        lecturer: { include: { user: true } },
        _count: { select: { enrollments: true } },
      },
      orderBy: { course: { code: "asc" } },
    });
    res.json({ offerings });
  }),
);

academicRouter.post(
  "/offerings",
  authorize("ADMIN"),
  asyncHandler(async (req, res) => {
    const data = z.object({ courseId: z.string(), semesterId: z.string(), lecturerId: z.string() }).parse(req.body);
    const offering = await prisma.courseOffering.create({ data });
    res.status(201).json({ offering });
  }),
);

academicRouter.get(
  "/offerings/:id/roster",
  authorize("ADMIN", "ACADEMIC_OFFICER", "LECTURER"),
  asyncHandler(async (req, res) => {
    const offeringId = String(req.params.id);
    await assertLecturerOffering(req.user!.lecturerId, offeringId, req.user!.role);
    const offering = await prisma.courseOffering.findUnique({
      where: { id: offeringId },
      include: {
        course: true,
        semester: true,
        assessments: { include: { marks: true } },
        enrollments: {
          include: {
            student: { include: { user: true, compliance: { take: 1, orderBy: { computedAt: "desc" } } } },
            grade: true,
            attendance: true,
          },
        },
      },
    });
    if (!offering) throw new HttpError(404, "Offering not found");
    res.json({ offering });
  }),
);

academicRouter.get(
  "/enrollments",
  asyncHandler(async (req, res) => {
    if (req.user!.role === "STUDENT") {
      const enrollments = await prisma.enrollment.findMany({
        where: { studentId: req.user!.studentId },
        include: { offering: { include: { course: true, semester: true } }, grade: true },
      });
      return res.json({ enrollments });
    }
    const enrollments = await prisma.enrollment.findMany({
      include: {
        student: { include: { user: true } },
        offering: { include: { course: true, semester: true } },
        grade: true,
      },
      take: 200,
    });
    res.json({ enrollments });
  }),
);

academicRouter.post(
  "/enrollments",
  authorize("ADMIN", "ACADEMIC_OFFICER"),
  asyncHandler(async (req, res) => {
    const data = z.object({ studentId: z.string(), offeringId: z.string() }).parse(req.body);
    const enrollment = await prisma.enrollment.create({ data });
    await recomputeStudentCompliance(data.studentId);
    res.status(201).json({ enrollment });
  }),
);

academicRouter.post(
  "/assessments",
  authorize("ADMIN", "LECTURER"),
  asyncHandler(async (req, res) => {
    const data = z
      .object({
        offeringId: z.string(),
        title: z.string(),
        type: z.enum(["CAT", "ASSIGNMENT", "EXAM"]),
        maxScore: z.number().positive().optional(),
        weight: z.number().min(0).max(1),
        dueDate: z.string().optional(),
      })
      .parse(req.body);
    await assertLecturerOffering(req.user!.lecturerId, data.offeringId, req.user!.role);
    const assessment = await prisma.assessment.create({
      data: {
        offeringId: data.offeringId,
        title: data.title,
        type: data.type,
        weight: data.weight,
        maxScore: data.maxScore ?? 100,
        dueDate: data.dueDate ? new Date(data.dueDate) : undefined,
      },
    });
    res.status(201).json({ assessment });
  }),
);

academicRouter.put(
  "/marks",
  authorize("ADMIN", "LECTURER"),
  asyncHandler(async (req, res) => {
    const data = z
      .object({
        assessmentId: z.string(),
        studentId: z.string(),
        score: z.number().min(0),
      })
      .parse(req.body);
    const assessment = await prisma.assessment.findUnique({ where: { id: data.assessmentId } });
    if (!assessment) throw new HttpError(404, "Assessment not found");
    await assertLecturerOffering(req.user!.lecturerId, assessment.offeringId, req.user!.role);
    if (data.score > assessment.maxScore) throw new HttpError(400, "Score exceeds maximum");

    const existing = await prisma.mark.findUnique({
      where: { assessmentId_studentId: { assessmentId: data.assessmentId, studentId: data.studentId } },
    });
    const mark = await prisma.mark.upsert({
      where: { assessmentId_studentId: { assessmentId: data.assessmentId, studentId: data.studentId } },
      create: data,
      update: { score: data.score },
    });
    const enrollment = await prisma.enrollment.findFirst({
      where: { studentId: data.studentId, offeringId: assessment.offeringId },
    });
    if (enrollment) await recomputeEnrollmentGrade(enrollment.id);
    await recomputeStudentCompliance(data.studentId);
    await writeAudit({
      req,
      action: existing ? "MARKS_MODIFIED" : "MARKS_UPLOADED",
      entity: "Mark",
      entityId: mark.id,
    });
    res.json({ mark });
  }),
);

academicRouter.post(
  "/marks/csv",
  authorize("ADMIN", "LECTURER"),
  asyncHandler(async (req, res) => {
    const { offeringId, csv } = z.object({ offeringId: z.string(), csv: z.string().min(1) }).parse(req.body);
    await assertLecturerOffering(req.user!.lecturerId, offeringId, req.user!.role);
    const offering = await prisma.courseOffering.findUnique({
      where: { id: offeringId },
      include: { assessments: true, enrollments: { include: { student: true } } },
    });
    if (!offering) throw new HttpError(404, "Offering not found");
    const lines = csv.split(/\r?\n/).filter((l) => l.trim());
    const header = lines.shift()?.split(",").map((h) => h.trim().toLowerCase()) ?? [];
    const regIdx = header.indexOf("regno");
    const assessIdx = header.indexOf("assessment");
    const scoreIdx = header.indexOf("score");
    if (regIdx < 0 || assessIdx < 0 || scoreIdx < 0) {
      throw new HttpError(400, "CSV must include regno,assessment,score columns");
    }
    let count = 0;
    for (const line of lines) {
      const cols = line.split(",").map((c) => c.trim());
      const student = offering.enrollments.find((e) => e.student.regNo === cols[regIdx])?.student;
      const assessment = offering.assessments.find(
        (a) => a.title.toLowerCase() === cols[assessIdx].toLowerCase() || a.id === cols[assessIdx],
      );
      if (!student || !assessment) continue;
      await prisma.mark.upsert({
        where: { assessmentId_studentId: { assessmentId: assessment.id, studentId: student.id } },
        create: { assessmentId: assessment.id, studentId: student.id, score: Number(cols[scoreIdx]) },
        update: { score: Number(cols[scoreIdx]) },
      });
      const enrollment = offering.enrollments.find((e) => e.studentId === student.id);
      if (enrollment) await recomputeEnrollmentGrade(enrollment.id);
      count += 1;
    }
    for (const e of offering.enrollments) await recomputeStudentCompliance(e.studentId);
    await writeAudit({ req, action: "MARKS_UPLOADED", entity: "CourseOffering", entityId: offeringId, metadata: { count } });
    res.json({ imported: count });
  }),
);

academicRouter.put(
  "/attendance",
  authorize("ADMIN", "LECTURER"),
  asyncHandler(async (req, res) => {
    const data = z
      .object({
        enrollmentId: z.string(),
        sessionDate: z.string(),
        present: z.boolean(),
      })
      .parse(req.body);
    const enrollment = await prisma.enrollment.findUnique({ where: { id: data.enrollmentId } });
    if (!enrollment) throw new HttpError(404, "Enrollment not found");
    await assertLecturerOffering(req.user!.lecturerId, enrollment.offeringId, req.user!.role);
    const sessionDate = new Date(data.sessionDate);
    const record = await prisma.attendanceRecord.upsert({
      where: { enrollmentId_sessionDate: { enrollmentId: data.enrollmentId, sessionDate } },
      create: { enrollmentId: data.enrollmentId, sessionDate, status: data.present ? "PRESENT" : "ABSENT" },
      update: { status: data.present ? "PRESENT" : "ABSENT" },
    });
    await recomputeStudentCompliance(enrollment.studentId);
    await writeAudit({ req, action: "ATTENDANCE_MODIFIED", entity: "AttendanceRecord", entityId: record.id });
    res.json({ record });
  }),
);

academicRouter.post(
  "/attendance/session",
  authorize("ADMIN", "LECTURER"),
  asyncHandler(async (req, res) => {
    const data = z
      .object({
        offeringId: z.string(),
        sessionDate: z.string(),
        records: z.array(z.object({ enrollmentId: z.string(), present: z.boolean() })),
      })
      .parse(req.body);
    await assertLecturerOffering(req.user!.lecturerId, data.offeringId, req.user!.role);
    const sessionDate = new Date(data.sessionDate);
    for (const r of data.records) {
      await prisma.attendanceRecord.upsert({
        where: { enrollmentId_sessionDate: { enrollmentId: r.enrollmentId, sessionDate } },
        create: { enrollmentId: r.enrollmentId, sessionDate, status: r.present ? "PRESENT" : "ABSENT" },
        update: { status: r.present ? "PRESENT" : "ABSENT" },
      });
    }
    const enrollments = await prisma.enrollment.findMany({ where: { offeringId: data.offeringId } });
    for (const e of enrollments) await recomputeStudentCompliance(e.studentId);
    await writeAudit({ req, action: "ATTENDANCE_MODIFIED", entity: "CourseOffering", entityId: data.offeringId });
    res.json({ ok: true, count: data.records.length });
  }),
);

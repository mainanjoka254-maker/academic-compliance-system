import { Router } from "express";
import { z } from "zod";
import type { Prisma } from "@prisma/client";
import { prisma } from "../lib/prisma.js";
import { asyncHandler } from "../utils/asyncHandler.js";
import { authenticate, authorize } from "../middleware/auth.js";
import { HttpError } from "../utils/httpError.js";

export const studentsRouter = Router();
studentsRouter.use(authenticate);

studentsRouter.get(
  "/",
  authorize("ADMIN", "ACADEMIC_OFFICER", "LECTURER"),
  asyncHandler(async (req, res) => {
    const q = String(req.query.q ?? "").trim();
    const departmentId = String(req.query.departmentId ?? "");
    const programId = String(req.query.programId ?? "");
    const courseId = String(req.query.courseId ?? "");
    const semesterId = String(req.query.semesterId ?? "");
    const status = String(req.query.status ?? "");
    const risk = String(req.query.risk ?? "");

    const where: Prisma.StudentWhereInput = {};
    if (q) {
      where.OR = [
        { regNo: { contains: q, mode: "insensitive" } },
        { user: { firstName: { contains: q, mode: "insensitive" } } },
        { user: { lastName: { contains: q, mode: "insensitive" } } },
        { user: { email: { contains: q, mode: "insensitive" } } },
      ];
    }
    if (departmentId) where.program = { departmentId };
    if (programId) where.programId = programId;
    if (courseId || semesterId) {
      where.enrollments = {
        some: {
          ...(courseId ? { offering: { courseId } } : {}),
          ...(semesterId ? { offering: { semesterId } } : {}),
          ...(req.user!.role === "LECTURER" && req.user!.lecturerId
            ? { offering: { lecturerId: req.user!.lecturerId } }
            : {}),
        },
      };
    } else if (req.user!.role === "LECTURER" && req.user!.lecturerId) {
      where.enrollments = { some: { offering: { lecturerId: req.user!.lecturerId } } };
    }
    if (status || risk) {
      where.compliance = {
        some: {
          ...(status ? { status: status as Prisma.EnumComplianceStatusFilter } : {}),
          ...(risk ? { riskLevel: risk as Prisma.EnumRiskLevelFilter } : {}),
        },
      };
    }

    const students = await prisma.student.findMany({
      where,
      include: {
        user: { select: { firstName: true, lastName: true, email: true } },
        program: true,
        compliance: { orderBy: { computedAt: "desc" }, take: 1 },
      },
      orderBy: { regNo: "asc" },
    });
    res.json({ students });
  }),
);

studentsRouter.get(
  "/:id",
  asyncHandler(async (req, res) => {
    const studentId = String(req.params.id);
    if (req.user!.role === "STUDENT" && req.user!.studentId !== studentId) {
      throw new HttpError(403, "You may only view your own record");
    }
    const student = await prisma.student.findUnique({
      where: { id: studentId },
      include: {
        user: { select: { firstName: true, lastName: true, email: true } },
        program: true,
        enrollments: {
          include: {
            offering: { include: { course: true, semester: true, lecturer: { include: { user: true } } } },
            grade: true,
            attendance: true,
          },
        },
        alerts: { where: { isRead: false }, orderBy: { createdAt: "desc" } },
        recommendations: { orderBy: { createdAt: "desc" }, take: 5 },
        compliance: { orderBy: { computedAt: "desc" }, take: 3, include: { semester: true } },
      },
    });
    if (!student) throw new HttpError(404, "Student not found");

    if (req.user!.role === "LECTURER" && req.user!.lecturerId) {
      const allowed = student.enrollments.some((e) => e.offering.lecturerId === req.user!.lecturerId);
      if (!allowed) throw new HttpError(403, "Not assigned to this student");
    }
    res.json({ student });
  }),
);

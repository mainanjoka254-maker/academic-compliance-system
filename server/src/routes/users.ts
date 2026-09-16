import { Router } from "express";
import { z } from "zod";
import { Role } from "@prisma/client";
import { prisma } from "../config/prisma.js";
import { authenticate, authorize, type AuthedRequest } from "../middleware/auth.js";
import { writeAudit } from "../middleware/audit.js";
import { asyncHandler } from "../middleware/error.js";
import { hashPassword } from "../utils/crypto.js";
import { badRequest, forbidden, notFound } from "../utils/httpError.js";

export const usersRouter = Router();
usersRouter.use(authenticate);

const userSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).optional(),
  firstName: z.string().min(1),
  lastName: z.string().min(1),
  role: z.nativeEnum(Role),
  isActive: z.boolean().optional(),
  staffNo: z.string().optional(),
  departmentId: z.string().optional(),
  regNo: z.string().optional(),
  programId: z.string().optional(),
  yearOfStudy: z.number().int().min(1).max(8).optional(),
});

usersRouter.get(
  "/",
  authorize("ADMIN"),
  asyncHandler(async (req, res) => {
    const q = String(req.query.q ?? "");
    const role = req.query.role as Role | undefined;
    const users = await prisma.user.findMany({
      where: {
        role,
        OR: q
          ? [
              { email: { contains: q, mode: "insensitive" } },
              { firstName: { contains: q, mode: "insensitive" } },
              { lastName: { contains: q, mode: "insensitive" } },
            ]
          : undefined,
      },
      include: { student: true, lecturer: true, academicOfficer: true },
      orderBy: { lastName: "asc" },
    });
    res.json({ users: users.map(sanitize) });
  }),
);

usersRouter.post(
  "/",
  authorize("ADMIN"),
  asyncHandler(async (req, res) => {
    const data = userSchema.parse(req.body);
    const password = data.password ?? "Demo@12345";
    const user = await prisma.user.create({
      data: {
        email: data.email.toLowerCase(),
        passwordHash: await hashPassword(password),
        firstName: data.firstName,
        lastName: data.lastName,
        role: data.role,
        emailVerified: true,
        student:
          data.role === "STUDENT"
            ? { create: { regNo: data.regNo ?? `STU${Date.now()}`, programId: required(data.programId, "programId"), yearOfStudy: data.yearOfStudy ?? 1 } }
            : undefined,
        lecturer:
          data.role === "LECTURER"
            ? { create: { staffNo: data.staffNo ?? `LEC${Date.now()}`, departmentId: required(data.departmentId, "departmentId") } }
            : undefined,
        academicOfficer:
          data.role === "ACADEMIC_OFFICER"
            ? { create: { staffNo: data.staffNo ?? `OFF${Date.now()}`, departmentId: data.departmentId } }
            : undefined,
      },
      include: { student: true, lecturer: true, academicOfficer: true },
    });
    await writeAudit({ userId: (req as AuthedRequest).user.id, action: "USER_CREATED", entity: "User", entityId: user.id, req });
    res.status(201).json({ user: sanitize(user) });
  }),
);

usersRouter.put(
  "/:id",
  authorize("ADMIN"),
  asyncHandler(async (req, res) => {
    const data = userSchema.partial().parse(req.body);
    const userId = String(req.params.id);
    const existing = await prisma.user.findUnique({ where: { id: userId } });
    if (!existing) throw notFound("User not found");
    const user = await prisma.user.update({
      where: { id: userId },
      data: {
        email: data.email?.toLowerCase(),
        firstName: data.firstName,
        lastName: data.lastName,
        isActive: data.isActive,
        passwordHash: data.password ? await hashPassword(data.password) : undefined,
      },
    });
    res.json({ user: sanitize(user) });
  }),
);

usersRouter.delete(
  "/:id",
  authorize("ADMIN"),
  asyncHandler(async (req, res) => {
    const actor = (req as AuthedRequest).user;
    const userId = String(req.params.id);
    if (actor.id === userId) throw badRequest("You cannot delete your own account");
    await prisma.user.delete({ where: { id: userId } });
    await writeAudit({ userId: actor.id, action: "USER_DELETED", entity: "User", entityId: userId, req });
    res.json({ ok: true });
  }),
);

export const studentsRouter = Router();
studentsRouter.use(authenticate);

studentsRouter.get(
  "/",
  authorize("ADMIN", "ACADEMIC_OFFICER", "LECTURER"),
  asyncHandler(async (req, res) => {
    const user = (req as AuthedRequest).user;
    const q = String(req.query.q ?? "");
    const { departmentId, programId, courseId, semesterId, status, riskLevel } = req.query as Record<string, string>;
    let lecturerStudentIds: string[] | undefined;
    if (user.role === "LECTURER" && user.lecturerId) {
      const enrollments = await prisma.enrollment.findMany({
        where: {
          offering: {
            lecturerId: user.lecturerId,
            ...(courseId ? { courseId } : {}),
            ...(semesterId ? { semesterId } : {}),
          },
        },
        select: { studentId: true },
      });
      lecturerStudentIds = [...new Set(enrollments.map((e) => e.studentId))];
    }
    const students = await prisma.student.findMany({
      where: {
        id: lecturerStudentIds ? { in: lecturerStudentIds } : undefined,
        programId: programId || undefined,
        program: departmentId ? { departmentId } : undefined,
        OR: q
          ? [
              { regNo: { contains: q, mode: "insensitive" } },
              { user: { firstName: { contains: q, mode: "insensitive" } } },
              { user: { lastName: { contains: q, mode: "insensitive" } } },
            ]
          : undefined,
        compliance: status || riskLevel ? { some: { status: status as never, riskLevel: riskLevel as never } } : undefined,
      },
      include: {
        user: true,
        program: { include: { department: { include: { school: true } } } },
        compliance: { orderBy: { computedAt: "desc" }, take: 1 },
      },
      orderBy: { regNo: "asc" },
    });
    res.json({ students });
  }),
);

studentsRouter.get(
  "/:id",
  authenticate,
  asyncHandler(async (req, res) => {
    const user = (req as AuthedRequest).user;
    const studentId = String(req.params.id);
    if (user.role === "STUDENT" && user.studentId !== studentId) throw forbidden();
    const student = await prisma.student.findUnique({
      where: { id: studentId },
      include: {
        user: true,
        program: { include: { department: { include: { school: true } } } },
        enrollments: {
          include: {
            grade: true,
            attendance: true,
            offering: { include: { course: true, semester: true, lecturer: { include: { user: true } }, assessments: { include: { marks: true } } } },
          },
        },
        compliance: { orderBy: { computedAt: "desc" }, include: { semester: true } },
        alerts: { orderBy: { createdAt: "desc" }, take: 20 },
        recommendations: { orderBy: { createdAt: "desc" }, take: 5 },
      },
    });
    if (!student) throw notFound("Student not found");
    if (user.role === "LECTURER" && user.lecturerId) {
      const allowed = student.enrollments.some((e) => e.offering.lecturerId === user.lecturerId);
      if (!allowed) throw forbidden();
    }
    res.json({ student });
  }),
);

function sanitize(user: any) {
  const { passwordHash, otpCode, resetToken, ...rest } = user;
  return rest;
}

function required(value: string | undefined, name: string) {
  if (!value) throw badRequest(`${name} is required`);
  return value;
}

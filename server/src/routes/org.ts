import { Router } from "express";
import { z } from "zod";
import { prisma } from "../config/prisma.js";
import { authenticate, authorize, type AuthedRequest } from "../middleware/auth.js";
import { asyncHandler } from "../middleware/error.js";
import { notFound } from "../utils/httpError.js";

export const orgRouter = Router();
orgRouter.use(authenticate);

const schoolSchema = z.object({ name: z.string().min(2), code: z.string().min(2) });
const deptSchema = z.object({ name: z.string().min(2), code: z.string().min(2), schoolId: z.string() });
const programSchema = z.object({
  name: z.string().min(2),
  code: z.string().min(2),
  departmentId: z.string(),
  requiredCredits: z.number().int().positive().optional(),
});
const courseSchema = z.object({
  code: z.string().min(2),
  title: z.string().min(2),
  credits: z.number().int().min(1).max(12).optional(),
  isCore: z.boolean().optional(),
  departmentId: z.string(),
  programId: z.string().optional().nullable(),
  prerequisiteIds: z.array(z.string()).optional(),
});
const yearSchema = z.object({
  name: z.string().min(2),
  startsOn: z.string(),
  endsOn: z.string(),
  isCurrent: z.boolean().optional(),
});
const semesterSchema = z.object({
  name: z.string().min(1),
  academicYearId: z.string(),
  startsOn: z.string(),
  endsOn: z.string(),
  isCurrent: z.boolean().optional(),
});

orgRouter.get("/schools", asyncHandler(async (_req, res) => {
  res.json({ schools: await prisma.school.findMany({ include: { departments: true }, orderBy: { name: "asc" } }) });
}));
orgRouter.post("/schools", authorize("ADMIN"), asyncHandler(async (req, res) => {
  const data = schoolSchema.parse(req.body);
  res.status(201).json({ school: await prisma.school.create({ data }) });
}));
orgRouter.put("/schools/:id", authorize("ADMIN"), asyncHandler(async (req, res) => {
  const data = schoolSchema.partial().parse(req.body);
  res.json({ school: await prisma.school.update({ where: { id: String(req.params.id) }, data }) });
}));
orgRouter.delete("/schools/:id", authorize("ADMIN"), asyncHandler(async (req, res) => {
  await prisma.school.delete({ where: { id: String(req.params.id) } });
  res.json({ ok: true });
}));

orgRouter.get("/departments", asyncHandler(async (req, res) => {
  const schoolId = req.query.schoolId as string | undefined;
  res.json({
    departments: await prisma.department.findMany({
      where: { schoolId },
      include: { school: true, _count: { select: { programs: true, lecturers: true } } },
      orderBy: { name: "asc" },
    }),
  });
}));
orgRouter.post("/departments", authorize("ADMIN"), asyncHandler(async (req, res) => {
  res.status(201).json({ department: await prisma.department.create({ data: deptSchema.parse(req.body) }) });
}));
orgRouter.put("/departments/:id", authorize("ADMIN"), asyncHandler(async (req, res) => {
  res.json({ department: await prisma.department.update({ where: { id: String(req.params.id) }, data: deptSchema.partial().parse(req.body) }) });
}));
orgRouter.delete("/departments/:id", authorize("ADMIN"), asyncHandler(async (req, res) => {
  await prisma.department.delete({ where: { id: String(req.params.id) } });
  res.json({ ok: true });
}));

orgRouter.get("/programs", asyncHandler(async (req, res) => {
  const departmentId = req.query.departmentId as string | undefined;
  res.json({
    programs: await prisma.program.findMany({
      where: { departmentId },
      include: { department: true, _count: { select: { students: true, courses: true } } },
      orderBy: { name: "asc" },
    }),
  });
}));
orgRouter.post("/programs", authorize("ADMIN"), asyncHandler(async (req, res) => {
  res.status(201).json({ program: await prisma.program.create({ data: programSchema.parse(req.body) }) });
}));
orgRouter.put("/programs/:id", authorize("ADMIN"), asyncHandler(async (req, res) => {
  res.json({ program: await prisma.program.update({ where: { id: String(req.params.id) }, data: programSchema.partial().parse(req.body) }) });
}));
orgRouter.delete("/programs/:id", authorize("ADMIN"), asyncHandler(async (req, res) => {
  await prisma.program.delete({ where: { id: String(req.params.id) } });
  res.json({ ok: true });
}));

orgRouter.get("/courses", asyncHandler(async (req, res) => {
  const { departmentId, programId, q } = req.query as Record<string, string>;
  res.json({
    courses: await prisma.course.findMany({
      where: {
        departmentId: departmentId || undefined,
        programId: programId || undefined,
        OR: q ? [{ code: { contains: q, mode: "insensitive" } }, { title: { contains: q, mode: "insensitive" } }] : undefined,
      },
      include: { department: true, program: true, prerequisites: { include: { prerequisite: true } } },
      orderBy: { code: "asc" },
    }),
  });
}));
orgRouter.post("/courses", authorize("ADMIN"), asyncHandler(async (req, res) => {
  const data = courseSchema.parse(req.body);
  const course = await prisma.course.create({
    data: {
      code: data.code,
      title: data.title,
      credits: data.credits ?? 3,
      isCore: data.isCore ?? true,
      departmentId: data.departmentId,
      programId: data.programId,
      prerequisites: data.prerequisiteIds?.length
        ? { create: data.prerequisiteIds.map((id) => ({ prerequisiteId: id })) }
        : undefined,
    },
  });
  res.status(201).json({ course });
}));
orgRouter.put("/courses/:id", authorize("ADMIN"), asyncHandler(async (req, res) => {
  const data = courseSchema.partial().parse(req.body);
  if (data.prerequisiteIds) {
    await prisma.coursePrerequisite.deleteMany({ where: { courseId: String(req.params.id) } });
  }
  const course = await prisma.course.update({
    where: { id: String(req.params.id) },
    data: {
      code: data.code,
      title: data.title,
      credits: data.credits,
      isCore: data.isCore,
      departmentId: data.departmentId,
      programId: data.programId,
      prerequisites: data.prerequisiteIds
        ? { create: data.prerequisiteIds.map((id) => ({ prerequisiteId: id })) }
        : undefined,
    },
  });
  res.json({ course });
}));
orgRouter.delete("/courses/:id", authorize("ADMIN"), asyncHandler(async (req, res) => {
  await prisma.course.delete({ where: { id: String(req.params.id) } });
  res.json({ ok: true });
}));

orgRouter.get("/academic-years", asyncHandler(async (_req, res) => {
  res.json({ years: await prisma.academicYear.findMany({ include: { semesters: true }, orderBy: { startsOn: "desc" } }) });
}));
orgRouter.post("/academic-years", authorize("ADMIN"), asyncHandler(async (req, res) => {
  const data = yearSchema.parse(req.body);
  if (data.isCurrent) await prisma.academicYear.updateMany({ data: { isCurrent: false } });
  res.status(201).json({
    year: await prisma.academicYear.create({
      data: { ...data, startsOn: new Date(data.startsOn), endsOn: new Date(data.endsOn) },
    }),
  });
}));
orgRouter.put("/academic-years/:id", authorize("ADMIN"), asyncHandler(async (req, res) => {
  const data = yearSchema.partial().parse(req.body);
  if (data.isCurrent) await prisma.academicYear.updateMany({ data: { isCurrent: false } });
  res.json({
    year: await prisma.academicYear.update({
      where: { id: String(req.params.id) },
      data: {
        ...data,
        startsOn: data.startsOn ? new Date(data.startsOn) : undefined,
        endsOn: data.endsOn ? new Date(data.endsOn) : undefined,
      },
    }),
  });
}));

orgRouter.get("/semesters", asyncHandler(async (req, res) => {
  const academicYearId = req.query.academicYearId as string | undefined;
  res.json({
    semesters: await prisma.semester.findMany({
      where: { academicYearId },
      include: { academicYear: true },
      orderBy: { startsOn: "desc" },
    }),
  });
}));
orgRouter.post("/semesters", authorize("ADMIN"), asyncHandler(async (req, res) => {
  const data = semesterSchema.parse(req.body);
  if (data.isCurrent) await prisma.semester.updateMany({ data: { isCurrent: false } });
  res.status(201).json({
    semester: await prisma.semester.create({
      data: { ...data, startsOn: new Date(data.startsOn), endsOn: new Date(data.endsOn) },
    }),
  });
}));
orgRouter.put("/semesters/:id", authorize("ADMIN"), asyncHandler(async (req, res) => {
  const data = semesterSchema.partial().parse(req.body);
  if (data.isCurrent) await prisma.semester.updateMany({ data: { isCurrent: false } });
  res.json({
    semester: await prisma.semester.update({
      where: { id: String(req.params.id) },
      data: {
        ...data,
        startsOn: data.startsOn ? new Date(data.startsOn) : undefined,
        endsOn: data.endsOn ? new Date(data.endsOn) : undefined,
      },
    }),
  });
}));

orgRouter.get("/offerings", asyncHandler(async (req, res) => {
  const user = (req as AuthedRequest).user;
  const { semesterId, lecturerId, courseId } = req.query as Record<string, string>;
  const offerings = await prisma.courseOffering.findMany({
    where: {
      semesterId: semesterId || undefined,
      courseId: courseId || undefined,
      lecturerId: user.role === "LECTURER" ? user.lecturerId : lecturerId || undefined,
    },
    include: {
      course: true,
      semester: true,
      lecturer: { include: { user: true } },
      _count: { select: { enrollments: true, assessments: true } },
    },
    orderBy: { createdAt: "desc" },
  });
  res.json({ offerings });
}));
orgRouter.post("/offerings", authorize("ADMIN"), asyncHandler(async (req, res) => {
  const data = z.object({ courseId: z.string(), semesterId: z.string(), lecturerId: z.string() }).parse(req.body);
  res.status(201).json({ offering: await prisma.courseOffering.create({ data }) });
}));
orgRouter.get("/offerings/:id", asyncHandler(async (req, res) => {
  const offering = await prisma.courseOffering.findUnique({
    where: { id: String(req.params.id) },
    include: {
      course: true,
      semester: true,
      lecturer: { include: { user: true } },
      assessments: true,
      enrollments: { include: { student: { include: { user: true } }, grade: true, attendance: true } },
    },
  });
  if (!offering) throw notFound("Offering not found");
  res.json({ offering });
}));

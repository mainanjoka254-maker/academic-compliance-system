import { Router } from "express";
import { z } from "zod";
import { prisma } from "../config/prisma.js";
import { authenticate, authorize } from "../middleware/auth.js";
import { asyncHandler } from "../middleware/error.js";
import { writeAudit } from "../middleware/audit.js";
import { hashPassword, verifyPassword } from "../utils/crypto.js";
import { badRequest, notFound } from "../utils/httpError.js";

export const accountRouter = Router();
accountRouter.use(authenticate);

accountRouter.get("/profile", asyncHandler(async (req, res) => {
  const user = await prisma.user.findUnique({
    where: { id: req.user!.id },
    select: { id: true, email: true, firstName: true, lastName: true, role: true, emailVerified: true, createdAt: true, student: { include: { program: true } }, lecturer: true, academicOfficer: true },
  });
  if (!user) throw notFound("Profile not found");
  res.json({ profile: user });
}));

accountRouter.patch("/profile", asyncHandler(async (req, res) => {
  const data = z.object({ firstName: z.string().min(1).optional(), lastName: z.string().min(1).optional(), email: z.string().email().optional() }).parse(req.body);
  const profile = await prisma.user.update({ where: { id: req.user!.id }, data: { ...data, email: data.email?.toLowerCase() }, select: { id: true, email: true, firstName: true, lastName: true, role: true } });
  await writeAudit({ req, action: "PROFILE_UPDATED", entity: "User", entityId: profile.id });
  res.json({ profile });
}));

accountRouter.patch("/password", asyncHandler(async (req, res) => {
  const data = z.object({ currentPassword: z.string().min(8), newPassword: z.string().min(12) }).parse(req.body);
  const user = await prisma.user.findUnique({ where: { id: req.user!.id } });
  if (!user || !(await verifyPassword(data.currentPassword, user.passwordHash))) throw badRequest("Current password is incorrect");
  await prisma.user.update({ where: { id: user.id }, data: { passwordHash: await hashPassword(data.newPassword) } });
  await writeAudit({ req, action: "PASSWORD_CHANGED", entity: "User", entityId: user.id });
  res.json({ ok: true });
}));

accountRouter.get("/notifications", asyncHandler(async (req, res) => {
  const notifications = await prisma.notification.findMany({ where: { userId: req.user!.id }, orderBy: { createdAt: "desc" }, take: 50 });
  res.json({ notifications, unread: notifications.filter((item) => !item.isRead).length });
}));

accountRouter.post("/notifications/read-all", asyncHandler(async (req, res) => {
  await prisma.notification.updateMany({ where: { userId: req.user!.id, isRead: false }, data: { isRead: true } });
  res.json({ ok: true });
}));

accountRouter.patch("/notifications/:id/read", asyncHandler(async (req, res) => {
  const notification = await prisma.notification.updateMany({ where: { id: String(req.params.id), userId: req.user!.id }, data: { isRead: true } });
  if (!notification.count) throw notFound("Notification not found");
  res.json({ ok: true });
}));

accountRouter.get("/settings", asyncHandler(async (req, res) => {
  const settings = await prisma.userSettings.upsert({ where: { userId: req.user!.id }, create: { userId: req.user!.id }, update: {} });
  res.json({ settings });
}));

accountRouter.patch("/settings", asyncHandler(async (req, res) => {
  const data = z.object({ emailNotifications: z.boolean().optional(), inAppNotifications: z.boolean().optional(), digestFrequency: z.enum(["IMMEDIATE", "DAILY", "WEEKLY", "NEVER"]).optional(), language: z.string().min(2).max(10).optional(), timezone: z.string().min(2).max(50).optional() }).parse(req.body);
  const settings = await prisma.userSettings.upsert({ where: { userId: req.user!.id }, create: { userId: req.user!.id, ...data }, update: data });
  await writeAudit({ req, action: "ACCOUNT_SETTINGS_UPDATED", entity: "UserSettings", entityId: settings.id });
  res.json({ settings });
}));

accountRouter.get("/audit", authorize("ADMIN"), asyncHandler(async (_req, res) => {
  const logs = await prisma.auditLog.findMany({ include: { user: { select: { firstName: true, lastName: true, email: true } } }, orderBy: { createdAt: "desc" }, take: 200 });
  res.json({ logs });
}));
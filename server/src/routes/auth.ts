import { Router } from "express";
import { z } from "zod";
import { prisma } from "../config/prisma.js";
import { env } from "../config/env.js";
import { asyncHandler } from "../middleware/error.js";
import { authenticate, type AuthedRequest } from "../middleware/auth.js";
import { writeAudit } from "../middleware/audit.js";
import { cookieOptions, hashPassword, randomOtp, randomToken, signToken, verifyPassword } from "../utils/crypto.js";
import { badRequest, unauthorized } from "../utils/httpError.js";
import { sendMail } from "../utils/mail.js";

export const authRouter = Router();

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

authRouter.post(
  "/login",
  asyncHandler(async (req, res) => {
    const { email, password } = loginSchema.parse(req.body);
    const user = await prisma.user.findUnique({
      where: { email: email.toLowerCase() },
      include: { student: true, lecturer: true, academicOfficer: true },
    });
    if (!user || !(await verifyPassword(password, user.passwordHash))) {
      throw unauthorized("Invalid email or password");
    }
    if (!user.isActive) throw unauthorized("Account is inactive");
    const token = signToken({ sub: user.id, email: user.email, role: user.role });
    res.cookie("token", token, cookieOptions());
    await writeAudit({ userId: user.id, action: "LOGIN", req });
    res.json({
      user: publicUser(user),
      token,
    });
  }),
);

authRouter.post(
  "/logout",
  authenticate,
  asyncHandler(async (req, res) => {
    const user = (req as AuthedRequest).user;
    res.clearCookie("token", { path: "/" });
    await writeAudit({ userId: user.id, action: "LOGOUT", req });
    res.json({ ok: true });
  }),
);

authRouter.get(
  "/me",
  authenticate,
  asyncHandler(async (req, res) => {
    const user = (req as AuthedRequest).user;
    const full = await prisma.user.findUnique({
      where: { id: user.id },
      include: { student: { include: { program: { include: { department: true } } } }, lecturer: true, academicOfficer: true },
    });
    res.json({ user: publicUser(full) });
  }),
);

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  firstName: z.string().min(1),
  lastName: z.string().min(1),
  regNo: z.string().min(3),
  programId: z.string().min(1),
});

authRouter.post(
  "/register",
  asyncHandler(async (req, res) => {
    if (!env.allowStudentRegister) throw badRequest("Student self-registration is disabled");
    const data = registerSchema.parse(req.body);
    const exists = await prisma.user.findUnique({ where: { email: data.email.toLowerCase() } });
    if (exists) throw badRequest("Email is already registered");
    const otp = randomOtp();
    const user = await prisma.user.create({
      data: {
        email: data.email.toLowerCase(),
        passwordHash: await hashPassword(data.password),
        firstName: data.firstName,
        lastName: data.lastName,
        role: "STUDENT",
        otpCode: otp,
        otpExpiresAt: new Date(Date.now() + 15 * 60 * 1000),
        student: { create: { regNo: data.regNo, programId: data.programId } },
      },
    });
    await sendMail(user.email, "Verify your academic account", `Your verification OTP is ${otp}`);
    await writeAudit({ userId: user.id, action: "USER_CREATED", entity: "User", entityId: user.id, req });
    res.status(201).json({ message: "Registered. Verify the OTP sent to your email (or shown in server logs in development)." });
  }),
);

authRouter.post(
  "/verify-otp",
  asyncHandler(async (req, res) => {
    const { email, otp } = z.object({ email: z.string().email(), otp: z.string().length(6) }).parse(req.body);
    const user = await prisma.user.findUnique({ where: { email: email.toLowerCase() } });
    if (!user?.otpCode || !user.otpExpiresAt || user.otpExpiresAt < new Date() || user.otpCode !== otp) {
      throw badRequest("Invalid or expired OTP");
    }
    await prisma.user.update({
      where: { id: user.id },
      data: { emailVerified: true, otpCode: null, otpExpiresAt: null },
    });
    res.json({ ok: true });
  }),
);

authRouter.post(
  "/forgot-password",
  asyncHandler(async (req, res) => {
    const { email } = z.object({ email: z.string().email() }).parse(req.body);
    const user = await prisma.user.findUnique({ where: { email: email.toLowerCase() } });
    if (user) {
      const token = randomToken();
      await prisma.user.update({
        where: { id: user.id },
        data: { resetToken: token, resetTokenExpiry: new Date(Date.now() + 60 * 60 * 1000) },
      });
      await sendMail(
        user.email,
        "Password reset",
        `Use this reset token with POST /api/auth/reset-password. Token: ${token}\nOr open ${env.clientOrigin}/reset-password?token=${token}`,
      );
    }
    res.json({ message: "If the account exists, reset instructions were sent." });
  }),
);

authRouter.post(
  "/reset-password",
  asyncHandler(async (req, res) => {
    const { token, password } = z.object({ token: z.string().min(10), password: z.string().min(8) }).parse(req.body);
    const user = await prisma.user.findFirst({
      where: { resetToken: token, resetTokenExpiry: { gt: new Date() } },
    });
    if (!user) throw badRequest("Invalid or expired reset token");
    await prisma.user.update({
      where: { id: user.id },
      data: { passwordHash: await hashPassword(password), resetToken: null, resetTokenExpiry: null },
    });
    await writeAudit({ userId: user.id, action: "PASSWORD_RESET", entity: "User", entityId: user.id, req });
    res.json({ ok: true });
  }),
);

function publicUser(user: any) {
  if (!user) return null;
  return {
    id: user.id,
    email: user.email,
    firstName: user.firstName,
    lastName: user.lastName,
    role: user.role,
    emailVerified: user.emailVerified,
    student: user.student ?? null,
    lecturer: user.lecturer ?? null,
    academicOfficer: user.academicOfficer ?? null,
  };
}

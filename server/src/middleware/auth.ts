import type { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";
import { env } from "../config/env.js";
import { prisma } from "../config/prisma.js";
import { forbidden, unauthorized } from "../utils/httpError.js";
import type { Role } from "@prisma/client";

export type AuthUser = {
  id: string;
  email: string;
  role: Role;
  firstName: string;
  lastName: string;
  studentId?: string;
  lecturerId?: string;
  officerId?: string;
};

export type AuthedRequest = Request & { user: AuthUser };

declare global {
  namespace Express {
    interface Request {
      user?: AuthUser;
    }
  }
}

export function authenticate(req: Request, _res: Response, next: NextFunction) {
  const token = req.cookies?.token || bearer(req.headers.authorization);
  if (!token) return next(unauthorized("Authentication required"));
  try {
    const payload = jwt.verify(token, env.jwtSecret) as { sub: string; role: Role; email: string };
    prisma.user
      .findUnique({
        where: { id: payload.sub },
        include: { student: true, lecturer: true, academicOfficer: true },
      })
      .then((user) => {
        if (!user || !user.isActive) return next(unauthorized("Account is inactive"));
        (req as AuthedRequest).user = {
          id: user.id,
          email: user.email,
          role: user.role,
          firstName: user.firstName,
          lastName: user.lastName,
          studentId: user.student?.id,
          lecturerId: user.lecturer?.id,
          officerId: user.academicOfficer?.id,
        };
        next();
      })
      .catch(next);
  } catch {
    next(unauthorized("Invalid or expired session"));
  }
}

export function authorize(...roles: Role[]) {
  return (req: Request, _res: Response, next: NextFunction) => {
    const user = (req as AuthedRequest).user;
    if (!user) return next(unauthorized());
    if (!roles.includes(user.role)) return next(forbidden("You do not have permission for this action"));
    next();
  };
}

function bearer(header?: string) {
  if (!header?.startsWith("Bearer ")) return undefined;
  return header.slice(7);
}

import type { Request } from "express";
import { prisma } from "../config/prisma.js";
import type { AuthUser } from "./auth.js";

export async function writeAudit(params: {
  userId?: string | null;
  action: string;
  entity?: string;
  entityId?: string;
  metadata?: unknown;
  req?: Request;
}) {
  await prisma.auditLog.create({
    data: {
      userId: params.userId ?? null,
      action: params.action,
      entity: params.entity,
      entityId: params.entityId,
      metadata: params.metadata as object | undefined,
      ip: params.req?.ip,
      userAgent: params.req?.get("user-agent") ?? undefined,
    },
  });
}

export function actor(user?: AuthUser) {
  return user?.id;
}

import { env } from "../config/env.js";

export async function sendMail(to: string, subject: string, text: string) {
  if (!env.smtp.host) {
    console.log(`[mail-dev] to=${to} subject=${subject}\n${text}`);
    return { delivered: false, logged: true };
  }
  const { createTransport } = await import("nodemailer").catch(() => ({ createTransport: null as any }));
  if (!createTransport) {
    console.log(`[mail-fallback] to=${to} subject=${subject}\n${text}`);
    return { delivered: false, logged: true };
  }
  const transport = createTransport({
    host: env.smtp.host,
    port: env.smtp.port,
    auth: env.smtp.user ? { user: env.smtp.user, pass: env.smtp.pass } : undefined,
  });
  await transport.sendMail({ from: env.smtp.from, to, subject, text });
  return { delivered: true, logged: false };
}

// frontend/middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// หน้า public ที่ไม่ต้องล็อกอิน
const PUBLIC_PATHS = [
  "/",                         // landing (ถ้ามี)
  "/community",                // หน้ารวม community
  "/community/",               // ป้องกัน edge case
  "/community/(.*)",           // ทุกหน้าภายใต้ community
  "/login",
  "/register",
  "/_next", "/favicon.ico", "/images", "/fonts",
];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // อนุญาตเส้นทาง public
  const isPublic = PUBLIC_PATHS.some((p) => {
    if (p.endsWith("(.*)")) {
      const base = p.replace("/(.*)", "");
      return pathname.startsWith(base);
    }
    return pathname === p || pathname.startsWith(p + "/");
  });

  if (isPublic) return NextResponse.next();

  // เช็ค token ในคุกกี้
  const token = req.cookies.get("access_token")?.value;
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname); // กลับมาหน้าเดิมหลังล็อกอิน
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  // ใช้กับทุกเส้นทาง (ยกเว้นไฟล์ static จะถูกกรองด้วย PUBLIC_PATHS ข้างบน)
  matcher: ["/((?!api).*)"],
};

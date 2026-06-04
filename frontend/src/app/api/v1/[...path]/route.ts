import { NextRequest, NextResponse } from "next/server";

// Read once at server start — this is a Node.js runtime env var injected by
// the container orchestrator (k8s, Docker Compose, etc.), so it is available
// at server startup time, unlike build-time env vars baked into the bundle.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

async function proxy(request: NextRequest): Promise<NextResponse> {
  const { pathname, search } = request.nextUrl;
  const targetUrl = `${BACKEND_URL}${pathname}${search}`;

  const headers = new Headers(request.headers);
  // Remove the Host header so the backend receives its own hostname, not the
  // frontend's, which would confuse virtual-host routing.
  headers.delete("host");

  const init: RequestInit & { duplex?: string } = {
    method: request.method,
    headers,
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
    // Required by the Fetch spec when body is a ReadableStream.
    init.duplex = "half";
  }

  const backendRes = await fetch(targetUrl, init);

  return new NextResponse(backendRes.body, {
    status: backendRes.status,
    statusText: backendRes.statusText,
    headers: backendRes.headers,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;

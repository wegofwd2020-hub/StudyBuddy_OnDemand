/**
 * Demo-mode flag.
 *
 * `demo.studybuddy.app` and any other deployment that should NOT surface
 * the school-registration / pricing flows reads `NEXT_PUBLIC_DEMO_MODE=true`
 * from its environment. Production deployments leave the variable unset
 * (or set it to anything other than the literal string `"true"`) so the
 * full marketing surface is visible.
 *
 * **Build-time vs runtime.** `NEXT_PUBLIC_*` variables are inlined into
 * the client bundle by Next.js at *build* time, not read at runtime.
 * This means:
 *   - For local dev (`npm run dev`) the flag must be in `.env.local` (or
 *     similar) before the dev server starts.
 *   - For Docker production builds the value must reach the build step
 *     via a Dockerfile `ARG` + the docker-compose `build.args` block —
 *     setting it only on the runtime container has no effect on the
 *     already-baked client bundle. (TODO when the demo Dockerfile is
 *     finalised: thread `NEXT_PUBLIC_DEMO_MODE` through.)
 *
 * **Why a constant, not a function.** Reading `process.env` once at
 * module-load gives every consumer the same value within a render pass
 * and lets the bundler dead-code-eliminate the alternate branch when
 * the flag is statically known. Using a function would keep both
 * branches in the bundle.
 */
export const IS_DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

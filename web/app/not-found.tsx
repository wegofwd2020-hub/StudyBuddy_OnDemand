import { LinkButton } from "@/components/ui/link-button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <h1 className="text-6xl font-bold text-gray-200">404</h1>
      <h2 className="mt-4 text-2xl font-semibold text-gray-900">Page not found</h2>
      <p className="mt-2 text-gray-500">
        The page you&apos;re looking for doesn&apos;t exist.
      </p>
      <LinkButton className="mt-6" href="/">
        Go home
      </LinkButton>
    </div>
  );
}

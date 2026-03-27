"use client";

import Link, { type LinkProps } from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { VariantProps } from "class-variance-authority";

type LinkButtonProps = LinkProps &
  VariantProps<typeof buttonVariants> & {
    className?: string;
    children: React.ReactNode;
  };

export function LinkButton({
  href,
  variant = "default",
  size = "default",
  className,
  children,
  ...props
}: LinkButtonProps) {
  return (
    <Link
      href={href}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    >
      {children}
    </Link>
  );
}

type AnchorButtonProps = React.AnchorHTMLAttributes<HTMLAnchorElement> &
  VariantProps<typeof buttonVariants> & {
    className?: string;
    children: React.ReactNode;
  };

export function AnchorButton({
  variant = "default",
  size = "default",
  className,
  children,
  ...props
}: AnchorButtonProps) {
  return (
    <a className={cn(buttonVariants({ variant, size }), className)} {...props}>
      {children}
    </a>
  );
}

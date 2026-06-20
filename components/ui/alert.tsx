import * as React from "react"

import { cn } from "@/lib/utils"

const alertVariants = {
  default:
    "border border-border bg-background text-foreground",
  destructive:
    "border border-destructive/50 bg-destructive/10 text-destructive-foreground",
}

type AlertVariant = keyof typeof alertVariants

function Alert({
  className,
  variant = "default",
  ...props
}: React.ComponentProps<"div"> & {
  variant?: AlertVariant
}) {
  return (
    <div className={cn("rounded-xl p-4 text-sm", alertVariants[variant], className)} {...props} />
  )
}

function AlertDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p className={cn("mt-2 text-sm text-muted-foreground", className)} {...props} />
  )
}

function AlertTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div className={cn("font-medium leading-none", className)} {...props} />
  )
}

export { Alert, AlertDescription, AlertTitle }

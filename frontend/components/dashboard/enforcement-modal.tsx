"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Checkbox } from "@/components/ui/checkbox"
import { Shield, AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react"
import { useAgentAction } from "@/hooks/use-agent-action"
import { executeEnforcement } from "@/lib/api"
import type { ForecastLatest, EnforcementResult } from "@/lib/types"

interface EnforcementModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  forecast: ForecastLatest | undefined
}

export function EnforcementModal({ open, onOpenChange, forecast }: EnforcementModalProps) {
  const [confirmed, setConfirmed] = useState(false)
  const [result, setResult] = useState<EnforcementResult | null>(null)

  const enforcementAction = useAgentAction({
    actionFn: executeEnforcement,
    queryKeysToInvalidate: ["status", "logs"],
    successMessage: "Enforcement actions executed successfully",
    errorMessage: "Failed to execute enforcement actions",
    onSuccess: (data) => setResult(data),
  })

  const handleClose = () => {
    setConfirmed(false)
    setResult(null)
    onOpenChange(false)
  }

  const handleExecute = async () => {
    await enforcementAction.execute()
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] bg-card border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-foreground">
            <Shield className="h-5 w-5 text-orange" />
            Authorize Autonomous Enforcement
          </DialogTitle>
          <DialogDescription>Review the current forecast and confirm enforcement authorization</DialogDescription>
        </DialogHeader>

        {!result ? (
          <>
            <Alert className="border-orange bg-orange/10">
              <AlertTriangle className="h-4 w-4 text-orange" />
              <AlertDescription className="text-orange">
                This action will trigger autonomous enforcement measures based on current air quality conditions. These
                actions may include construction bans, vehicle restrictions, and school advisories.
              </AlertDescription>
            </Alert>

            <Card className="p-4 bg-secondary/50 border-border">
              <h4 className="font-medium text-foreground mb-2">Current Forecast Reasoning</h4>
              <p className="text-sm text-muted-foreground">
                {forecast?.prediction?.reasoning ||
                  "No forecast reasoning available. Please run a forecast cycle first."}
              </p>
              <div className="flex items-center gap-2 mt-3">
                <Badge className="bg-orange text-white">{forecast?.prediction?.aqi_category || "Unknown"}</Badge>
                <span className="text-xs text-muted-foreground">
                  Confidence: {forecast?.prediction?.confidence_level || 0}%
                </span>
              </div>
            </Card>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="confirm"
                checked={confirmed}
                onCheckedChange={(checked) => setConfirmed(checked === true)}
              />
              <label
                htmlFor="confirm"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-foreground"
              >
                I understand and authorize autonomous enforcement actions
              </label>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                onClick={handleExecute}
                disabled={!confirmed || enforcementAction.isLoading}
                className="bg-orange hover:bg-orange/90 text-white gap-2"
              >
                {enforcementAction.isLoading ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Shield className="h-4 w-4" />
                )}
                Execute Enforcement
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <Alert className="border-success bg-success/10">
              <CheckCircle2 className="h-4 w-4 text-success" />
              <AlertDescription className="text-success">
                Enforcement actions have been successfully executed.
              </AlertDescription>
            </Alert>

            <div className="space-y-3">
              <h4 className="font-medium text-foreground">Executed Actions</h4>
              {result.actions.map((action, index) => (
                <Card key={index} className="p-3 bg-secondary/50 border-border">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground">
                      {action.type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                    </span>
                    <Badge
                      className={
                        action.status === "executed"
                          ? "bg-success/20 text-success"
                          : "bg-destructive/20 text-destructive"
                      }
                    >
                      {action.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{action.message}</p>
                </Card>
              ))}
            </div>

            <Card className="p-4 bg-secondary/50 border-border">
              <h4 className="font-medium text-foreground mb-2">Enforcement Reasoning</h4>
              <p className="text-sm text-muted-foreground">{result.reasoning}</p>
            </Card>

            <DialogFooter>
              <Button onClick={handleClose}>Close</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

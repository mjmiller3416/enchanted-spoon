"use client";

import { MessageSquare, Mail, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useFeedbackForm, FEEDBACK_CATEGORIES } from "@/hooks/forms/useFeedbackForm";
import { SectionHeader } from "../SectionHeader";
import { appConfig } from "@/lib/config";

export function FeedbackSection() {
  const {
    category,
    setCategory,
    message,
    setMessage,
    isSubmitting,
    canSubmit,
    handleSubmit,
    remainingChars,
  } = useFeedbackForm();

  return (
    <Card>
      <CardContent className="pt-6">
        <SectionHeader
          icon={MessageSquare}
          title="Send Feedback"
          description={`Help us improve ${appConfig.appName} by sharing your thoughts`}
        />

        <div className="space-y-6">
          {/* Category Selection */}
          <div className="space-y-2">
            <Label
              htmlFor="feedback-category"
              className="flex items-center gap-2"
            >
              <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
              Feedback Type
            </Label>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="max-w-md">
                <SelectValue placeholder="Select a category..." />
              </SelectTrigger>
              <SelectContent>
                {FEEDBACK_CATEGORIES.map((cat) => (
                  <SelectItem key={cat.value} value={cat.value}>
                    {cat.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Choose the type of feedback you&apos;re providing
            </p>
          </div>

          {/* Message */}
          <div className="space-y-2">
            <Label
              htmlFor="feedback-message"
              className="flex items-center gap-2"
            >
              <Mail className="h-3.5 w-3.5 text-muted-foreground" />
              Your Message
            </Label>
            <Textarea
              id="feedback-message"
              placeholder="Tell us what's on your mind... (minimum 10 characters)"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="min-h-40 max-w-2xl"
            />
            <p className="text-xs text-muted-foreground">
              Be as detailed as possible to help us understand your feedback
            </p>
          </div>

          <Separator />

          {/* Submit Button */}
          <div className="flex items-center gap-4">
            <Button
              onClick={handleSubmit}
              disabled={!canSubmit || isSubmitting}
              className="gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  Submit Feedback
                </>
              )}
            </Button>
            {!canSubmit &&
              category &&
              message.length > 0 &&
              remainingChars > 0 && (
                <p className="text-sm text-muted-foreground">
                  {remainingChars} more character
                  {remainingChars !== 1 ? "s" : ""} needed
                </p>
              )}
          </div>

          {/* Info Box */}
          <div className="bg-elevated rounded-xl p-4 border border-border">
            <p className="text-sm text-muted-foreground">
              Your feedback helps us prioritize improvements. Thank you
              for helping make {appConfig.appName} better!
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

import React, { useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Phone, CheckCircle } from "@phosphor-icons/react";
import { API, formatApiErrorDetail, useAuth } from "../../App";

const inputClass =
  "w-full px-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors";

/** Send a code to the account's phone (or a new number) and confirm it (FR-01, one account per phone). */
export default function PhoneVerify({ allowChange = false, onVerified }) {
  const { user, refreshUser, authConfig } = useAuth();
  const [newPhone, setNewPhone] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const verified = user?.phone_verified;

  const send = async () => {
    setError("");
    setBusy(true);
    try {
      const body = allowChange && newPhone.trim() ? { phone: newPhone.trim() } : {};
      await axios.post(`${API}/auth/phone/send-code`, body);
      setSent(true);
      toast.success("Code sent by text message");
      if (body.phone) await refreshUser();
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const verify = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await axios.post(`${API}/auth/phone/verify`, { code: code.trim() });
      toast.success("Phone number verified");
      await refreshUser();
      setSent(false);
      setCode("");
      setNewPhone("");
      onVerified && onVerified();
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="phone-verify">
      <div className="flex items-center gap-2 text-sm">
        <Phone className="h-5 w-5 text-muted-foreground" />
        <span className="font-medium">{user?.phone || "No phone number yet"}</span>
        {verified && !newPhone && (
          <span className="inline-flex items-center gap-1 text-primary font-medium">
            <CheckCircle className="h-4 w-4" weight="fill" /> Verified
          </span>
        )}
      </div>

      {allowChange && (
        <div>
          <label className="block text-sm font-medium mb-2" htmlFor="new_phone">
            {user?.phone ? "Change phone number" : "Phone number"}
          </label>
          <input
            id="new_phone"
            type="tel"
            value={newPhone}
            onChange={(e) => setNewPhone(e.target.value)}
            className={inputClass}
            placeholder="604-555-0123"
            data-testid="phone-new"
          />
        </div>
      )}

      {(!verified || newPhone.trim()) && (
        <button
          type="button"
          onClick={send}
          disabled={busy}
          className="px-4 py-2 bg-secondary text-white font-medium hover:bg-secondary/90 disabled:opacity-50"
          data-testid="phone-send-code"
        >
          {sent ? "Send a new code" : "Text me a code"}
        </button>
      )}

      {sent && (
        <form onSubmit={verify} className="flex gap-2 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-2" htmlFor="phone_code">6-digit code</label>
            <input
              id="phone_code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              className={inputClass}
              required
              data-testid="phone-code"
            />
          </div>
          <button
            type="submit"
            disabled={busy || code.length !== 6}
            className="px-4 py-3 bg-primary text-white font-bold hover:bg-primary/90 disabled:opacity-50"
            data-testid="phone-verify-submit"
          >
            Verify
          </button>
        </form>
      )}

      {sent && authConfig?.phone_verification === "dev" && (
        <p className="text-xs text-muted-foreground">Development mode: no text is sent — use 000000.</p>
      )}
      {error && <p className="text-sm text-destructive" data-testid="phone-error">{error}</p>}
    </div>
  );
}

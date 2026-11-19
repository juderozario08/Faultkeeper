import styled from "@emotion/styled";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useLogin, useMe } from "../api/hooks";
import { ThemeToggle } from "../components/ThemeToggle";
import { Button, Input, Panel } from "../components/ui";
import { color } from "../theme/tokens";

const Page = styled.div`
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: 24px;
`;

const Card = styled(Panel)`
  width: 100%;
  max-width: 380px;
  padding: 28px;
  display: grid;
  gap: 14px;
`;

const Label = styled.label`
  display: grid;
  gap: 6px;
  font-size: 13px;
  color: ${color.textMuted};
`;

export function LoginPage() {
  const me = useMe();
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const next = (location.state as { from?: string } | null)?.from ?? "/";

  if (me.data) return <Navigate to={next} replace />;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    login.mutate({ email, password }, { onSuccess: () => navigate(next, { replace: true }) });
  };

  return (
    <Page>
      <Card as="form" onSubmit={submit} aria-label="Sign in">
        <h1 style={{ margin: 0, fontSize: 20 }}>Sign in to Faultkeeper</h1>
        <Label>
          Email
          <Input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </Label>
        <Label>
          Password
          <Input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Label>
        {login.error && (
          <div role="alert" style={{ color: color.dangerText, fontSize: 13 }}>
            {login.error.message}
          </div>
        )}
        <Button variant="primary" type="submit" disabled={login.isPending} style={{ justifyContent: "center" }}>
          {login.isPending ? "Signing in…" : "Sign in"}
        </Button>
        <div style={{ display: "flex", justifyContent: "center" }}>
          <ThemeToggle />
        </div>
      </Card>
    </Page>
  );
}

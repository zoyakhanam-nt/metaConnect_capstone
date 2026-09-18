import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../auth.js";

export default function Login() {
  const [form, setForm] = useState({ username: "", password: "" });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const validate = () => {
    const errs = {};
    if (!form.username.trim()) errs.username = "Required";
    if (!form.password) errs.password = "Required";
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    setServerError(null);
    setBusy(true);
    try {
      console.log("Logging in with", form.username, form.password);
      await login(form.username, form.password);
      console.log("Login successful, navigating to /");
      navigate("/");
      console.log("Navigation complete");
    } catch (err) {
      setServerError(err.message);
    } finally {
      setBusy(false);
      console.log("Login process completed");
    }
  };

  return (
    <div className="login-wrap">
      <form className="login-form" onSubmit={handleSubmit} noValidate>
        <h1>Sign in</h1>
        {serverError && <p className="error">{serverError}</p>}

        <label>
          Username
          <input
            value={form.username}
            onChange={(e) =>
              setForm((f) => ({ ...f, username: e.target.value }))
            }
          />
          {errors.username && (
            <span className="field-error">{errors.username}</span>
          )}
        </label>

        <label>
          Password
          <input
            type="password"
            value={form.password}
            onChange={(e) =>
              setForm((f) => ({ ...f, password: e.target.value }))
            }
          />
          {errors.password && (
            <span className="field-error">{errors.password}</span>
          )}
        </label>

        <button type="submit" disabled={busy}>
          {busy ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}

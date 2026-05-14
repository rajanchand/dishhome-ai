import { useCallback, useEffect, useState } from "react";
import { api, type AdminUser, type Role } from "../lib/api";
import {
  Badge,
  Button,
  Card,
  Input,
  PageBody,
  PageHeader,
} from "../components/ui";
import { Skeleton } from "../components/Skeleton";
import { useAsyncErrorToast, useToast } from "../components/Toast";
import { useAuth } from "../lib/auth";

const ROLE_OPTIONS = ["super_admin", "admin", "supervisor", "agent"] as const;
type RoleId = (typeof ROLE_OPTIONS)[number];

export default function AccessPortal() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [roles, setRoles] = useState<Role[] | null>(null);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [creating, setCreating] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<AdminUser | null>(null);
  const errToast = useAsyncErrorToast();
  const toast = useToast();
  const { user: me } = useAuth();

  const canManageUsers = me?.permissions?.includes("users.manage") ?? false;

  const refresh = useCallback(async () => {
    try {
      const [u, r] = await Promise.all([
        api.get<AdminUser[]>("/admin/users"),
        api.get<Role[]>("/admin/roles"),
      ]);
      setUsers(u);
      setRoles(r);
    } catch (e) {
      errToast(e);
    }
  }, [errToast]);

  useEffect(() => {
    if (canManageUsers) refresh();
  }, [canManageUsers, refresh]);

  async function deleteUser(u: AdminUser) {
    try {
      await api.delete(`/admin/users/${u.username}`);
      toast.success("User deleted", u.username);
      refresh();
    } catch (e) {
      errToast(e);
    } finally {
      setConfirmDelete(null);
    }
  }

  if (!canManageUsers) {
    return (
      <>
        <PageHeader title="Access Portal" />
        <PageBody>
          <Card title="Forbidden">
            <p className="text-sm text-dishhome-ink/70">
              You don't have the <span className="font-mono">users.manage</span>
              {" "}permission. Ask a super_admin to grant you the
              admin role to manage users.
            </p>
            <p className="text-xs text-dishhome-ink/50 mt-2">
              Signed in as <span className="font-mono">{me?.username}</span>{" "}
              (role: <span className="font-mono">{me?.role}</span>).
            </p>
          </Card>
        </PageBody>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Access Portal"
        subtitle="Create users, assign roles, manage who can do what in DishHome AI."
        actions={<Button onClick={() => setCreating(true)}>+ New user</Button>}
      />
      <PageBody>
        <Card title="Roles">
          {!roles ? (
            <Skeleton className="h-24" />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {roles.map((r) => (
                <div
                  key={r.id}
                  className="border border-black/5 rounded-md p-4 bg-white"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-semibold text-dishhome-ink">{r.name}</div>
                    <Badge tone="info">
                      {r.user_count} user{r.user_count === 1 ? "" : "s"}
                    </Badge>
                  </div>
                  <div className="text-xs text-dishhome-ink/60 mb-2">
                    {r.permissions.length} permissions
                  </div>
                  <details className="text-xs">
                    <summary className="cursor-pointer text-dishhome-blue">
                      View permissions
                    </summary>
                    <ul className="mt-2 space-y-0.5 text-dishhome-ink/70 max-h-40 overflow-y-auto">
                      {r.permissions.map((p) => (
                        <li key={p} className="font-mono">{p}</li>
                      ))}
                    </ul>
                  </details>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Users" className="mt-6">
          {!users ? (
            <Skeleton className="h-40" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs uppercase tracking-widest text-dishhome-ink/60 border-b border-black/5">
                  <tr>
                    <th className="text-left py-2">Username</th>
                    <th className="text-left">Name</th>
                    <th className="text-left">Email</th>
                    <th className="text-left">Role</th>
                    <th className="text-left">Created</th>
                    <th className="text-right pr-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.username} className="border-b border-black/5">
                      <td className="py-2 font-mono">{u.username}</td>
                      <td>{u.name}</td>
                      <td className="text-dishhome-ink/70">{u.email}</td>
                      <td>
                        <Badge tone={roleTone(u.role)}>{u.role}</Badge>
                      </td>
                      <td className="text-xs text-dishhome-ink/60">
                        {u.created_at
                          ? new Date(u.created_at).toLocaleDateString()
                          : "seed"}
                      </td>
                      <td className="text-right pr-2 whitespace-nowrap">
                        <button
                          className="text-xs text-dishhome-blue hover:underline mr-3"
                          onClick={() => setEditing(u)}
                        >
                          Edit
                        </button>
                        <button
                          className="text-xs text-red-600 hover:underline disabled:opacity-40 disabled:no-underline disabled:cursor-not-allowed"
                          disabled={u.username === me?.username}
                          title={u.username === me?.username ? "Cannot delete yourself" : ""}
                          onClick={() => setConfirmDelete(u)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </PageBody>

      {creating && (
        <UserDialog
          mode="create"
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            refresh();
          }}
        />
      )}
      {editing && (
        <UserDialog
          mode="edit"
          user={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refresh();
          }}
        />
      )}
      {confirmDelete && (
        <ConfirmDialog
          title={`Delete ${confirmDelete.username}?`}
          body="They will lose access immediately and all their sessions will be revoked."
          confirmLabel="Delete user"
          danger
          onCancel={() => setConfirmDelete(null)}
          onConfirm={() => deleteUser(confirmDelete)}
        />
      )}
    </>
  );
}

function roleTone(role: string): "danger" | "warn" | "info" | "neutral" {
  switch (role) {
    case "super_admin":
      return "danger";
    case "admin":
      return "warn";
    case "supervisor":
      return "info";
    default:
      return "neutral";
  }
}

// ---- modal backdrop wrapper with escape-to-close ----
function Modal({
  onClose,
  children,
}: {
  onClose: () => void;
  children: React.ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-md p-6"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

function ConfirmDialog({
  title,
  body,
  confirmLabel,
  danger,
  onCancel,
  onConfirm,
}: {
  title: string;
  body: string;
  confirmLabel: string;
  danger?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <Modal onClose={onCancel}>
      <h2 className="text-lg font-semibold text-dishhome-ink mb-2">{title}</h2>
      <p className="text-sm text-dishhome-ink/70">{body}</p>
      <div className="flex gap-2 justify-end mt-6">
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
        <Button variant={danger ? "danger" : "primary"} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}

function UserDialog({
  mode,
  user,
  onClose,
  onSaved,
}: {
  mode: "create" | "edit";
  user?: AdminUser;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [username, setUsername] = useState(user?.username ?? "");
  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [role, setRole] = useState<RoleId>((user?.role as RoleId) ?? "agent");
  const [password, setPassword] = useState("");
  const [resetPw, setResetPw] = useState("");
  const [saving, setSaving] = useState(false);
  const errToast = useAsyncErrorToast();
  const toast = useToast();

  // Inline client validation matching the backend so the user sees the error
  // before submitting (rather than getting a 422 from the server).
  const usernameOk = mode === "edit" || /^[a-z0-9_.-]{3,40}$/.test(username);
  const nameOk = name.trim().length >= 2;
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const pwOk =
    mode === "edit"
      ? resetPw === "" || (resetPw.length >= 8 && !/^\d+$/.test(resetPw) && !/^[A-Za-z]+$/.test(resetPw))
      : password.length >= 8 && !/^\d+$/.test(password) && !/^[A-Za-z]+$/.test(password);
  const formOk = usernameOk && nameOk && emailOk && pwOk && !saving;

  async function save() {
    if (!formOk) return;
    setSaving(true);
    try {
      if (mode === "create") {
        await api.post("/admin/users", {
          username: username.trim().toLowerCase(),
          name: name.trim(),
          email: email.trim(),
          role,
          password,
        });
        toast.success("User created", username.toLowerCase());
      } else {
        // Only send fields the operator actually changed.
        const patch: Record<string, unknown> = {};
        if (name.trim() !== user!.name) patch.name = name.trim();
        if (email.trim() !== user!.email) patch.email = email.trim();
        if (role !== user!.role) patch.role = role;
        if (Object.keys(patch).length > 0) {
          await api.patch(`/admin/users/${user!.username}`, patch);
        }
        if (resetPw) {
          await api.post(`/admin/users/${user!.username}/reset-password`, {
            new_password: resetPw,
          });
        }
        toast.success(
          "User updated",
          Object.keys(patch).length === 0 && !resetPw
            ? "No changes"
            : user!.username,
        );
      }
      onSaved();
    } catch (e) {
      errToast(e);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal onClose={onClose}>
      <h2 className="text-lg font-semibold text-dishhome-ink mb-4">
        {mode === "create" ? "New user" : `Edit ${user!.username}`}
      </h2>
      <div className="space-y-3">
        {mode === "create" && (
          <div>
            <Input
              label="Username"
              value={username}
              onChange={(e) =>
                setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_.-]/g, ""))
              }
              placeholder="lowercase letters, numbers, _ . -"
            />
            {username && !usernameOk && (
              <p className="text-xs text-rose-600 mt-1">
                3–40 chars; lowercase letters, digits, _, ., -
              </p>
            )}
          </div>
        )}
        <Input
          label="Full name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <div>
          <label className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
            Role
          </label>
          <select
            className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30"
            value={role}
            onChange={(e) => setRole(e.target.value as RoleId)}
          >
            {ROLE_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        {mode === "create" && (
          <div>
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="min 8 chars, mix letters + numbers"
            />
            {password && !pwOk && (
              <p className="text-xs text-rose-600 mt-1">
                At least 8 characters and must mix letters and numbers.
              </p>
            )}
          </div>
        )}
        {mode === "edit" && (
          <div>
            <Input
              label="Reset password (leave blank to keep current)"
              type="password"
              value={resetPw}
              onChange={(e) => setResetPw(e.target.value)}
              placeholder="new password"
            />
            {resetPw && !pwOk && (
              <p className="text-xs text-rose-600 mt-1">
                At least 8 characters and must mix letters and numbers.
              </p>
            )}
          </div>
        )}
      </div>
      <div className="flex gap-2 justify-end mt-6">
        <Button variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={save} disabled={!formOk}>
          {saving ? "Saving…" : mode === "create" ? "Create" : "Save"}
        </Button>
      </div>
    </Modal>
  );
}

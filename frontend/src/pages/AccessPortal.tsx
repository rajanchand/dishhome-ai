import { useEffect, useState } from "react";
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

const ROLE_OPTIONS = ["super_admin", "admin", "supervisor", "agent"] as const;

export default function AccessPortal() {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [roles, setRoles] = useState<Role[] | null>(null);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [creating, setCreating] = useState(false);
  const errToast = useAsyncErrorToast();
  const toast = useToast();

  async function refresh() {
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
  }

  useEffect(() => {
    refresh();
  }, []);

  async function deleteUser(u: AdminUser) {
    if (!confirm(`Delete user ${u.username}? They will lose access immediately.`)) return;
    try {
      await api.delete(`/admin/users/${u.username}`);
      toast.success("User deleted", u.username);
      refresh();
    } catch (e) {
      errToast(e);
    }
  }

  return (
    <>
      <PageHeader
        title="Access Portal"
        subtitle="Create users, assign roles, manage who can do what in DishHome AI."
        actions={
          <Button onClick={() => setCreating(true)}>+ New user</Button>
        }
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
                  className="border border-dishhome-mist rounded-md p-4 bg-white"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-semibold text-dishhome-ink">{r.name}</div>
                    <Badge tone="info">{r.user_count} user{r.user_count === 1 ? "" : "s"}</Badge>
                  </div>
                  <div className="text-xs text-dishhome-ink/60 mb-2">
                    {r.permissions.length} permissions
                  </div>
                  <details className="text-xs">
                    <summary className="cursor-pointer text-dishhome-blue">
                      View permissions
                    </summary>
                    <ul className="mt-2 space-y-0.5 text-dishhome-ink/70">
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
            <table className="w-full text-sm">
              <thead className="text-xs uppercase tracking-widest text-dishhome-ink/60 border-b border-dishhome-mist">
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
                  <tr key={u.username} className="border-b border-dishhome-mist/50">
                    <td className="py-2 font-mono">{u.username}</td>
                    <td>{u.name}</td>
                    <td className="text-dishhome-ink/70">{u.email}</td>
                    <td><Badge tone={u.role === "super_admin" ? "danger" : u.role === "admin" ? "warn" : "info"}>{u.role}</Badge></td>
                    <td className="text-xs text-dishhome-ink/60">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "seed"}
                    </td>
                    <td className="text-right pr-2">
                      <button
                        className="text-xs text-dishhome-blue hover:underline mr-3"
                        onClick={() => setEditing(u)}
                      >
                        Edit
                      </button>
                      <button
                        className="text-xs text-red-600 hover:underline"
                        onClick={() => deleteUser(u)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
    </>
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
  const [role, setRole] = useState(user?.role ?? "agent");
  const [password, setPassword] = useState("");
  const [resetPw, setResetPw] = useState("");
  const [saving, setSaving] = useState(false);
  const errToast = useAsyncErrorToast();
  const toast = useToast();

  async function save() {
    setSaving(true);
    try {
      if (mode === "create") {
        await api.post("/admin/users", { username, name, email, role, password });
        toast.success("User created", username);
      } else {
        await api.patch(`/admin/users/${user!.username}`, { name, email, role });
        if (resetPw) {
          await api.post(`/admin/users/${user!.username}/reset-password`, {
            new_password: resetPw,
          });
        }
        toast.success("User updated", user!.username);
      }
      onSaved();
    } catch (e) {
      errToast(e);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-dishhome-ink mb-4">
          {mode === "create" ? "New user" : `Edit ${user!.username}`}
        </h2>
        <div className="space-y-3">
          {mode === "create" && (
            <Input
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="lowercase, letters/numbers/_.-"
            />
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
            <label className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1">
              Role
            </label>
            <select
              className="w-full border border-dishhome-mist rounded-md px-3 py-2 text-sm bg-white"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          {mode === "create" && (
            <Input
              label="Password (min 8 chars)"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          )}
          {mode === "edit" && (
            <Input
              label="Reset password (leave blank to keep current)"
              type="password"
              value={resetPw}
              onChange={(e) => setResetPw(e.target.value)}
              placeholder="new password (min 8 chars)"
            />
          )}
        </div>
        <div className="flex gap-2 justify-end mt-6">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} disabled={saving}>
            {saving ? "Saving…" : mode === "create" ? "Create" : "Save"}
          </Button>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { authApi, getApiErrorMessage, usersApi } from '../api';

const emptyForm = { username: '', first_name: '', last_name: '', phone: '', email: '', role: 'worker', password: '' };

/** Рабочий кабинет сотрудников. Сервер определяет допустимые роли и действия. */
export default function UsersPage() {
  const [profile, setProfile] = useState(null);
  const [rows, setRows] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [editing, setEditing] = useState(undefined);
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    authApi.me().then(({ data }) => { if (active) setProfile(data); })
      .catch((e) => { if (active) { setError(getApiErrorMessage(e)); setLoading(false); } });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!profile) return;
    if (!profile.manageable_roles?.length) { setLoading(false); return; }
    let active = true;
    setLoading(true);
    const timer = setTimeout(() => {
      usersApi.list({ search }).then(({ data }) => {
        if (active) { setRows(data.results ?? data); setError(''); }
      }).catch((e) => { if (active) setError(getApiErrorMessage(e)); })
        .finally(() => { if (active) setLoading(false); });
    }, 250);
    return () => { active = false; clearTimeout(timer); };
  }, [profile, search]);

  const open = (user = null) => {
    setEditing(user);
    setForm(user ? Object.fromEntries(Object.keys(emptyForm).map((key) => [key, key === 'password' ? '' : user[key] ?? ''])) : { ...emptyForm });
    setFormError('');
  };
  const save = async (event) => {
    event.preventDefault();
    if (saving) return;
    setSaving(true); setFormError(''); setMessage('');
    const payload = { ...form };
    if (editing && !payload.password) delete payload.password;
    try {
      if (editing) await usersApi.update(editing.id, payload);
      else await usersApi.create(payload);
      setEditing(undefined); setMessage('Сотрудник сохранён');
      // Новая ссылка запускает повторную загрузку с текущим поисковым запросом.
      setProfile((current) => ({ ...current }));
    } catch (e) { setFormError(getApiErrorMessage(e, 'Не удалось сохранить сотрудника')); }
    finally { setSaving(false); }
  };
  const field = (name, label, props = {}) => <TextField key={name} label={label} value={form[name]} onChange={(e) => setForm({ ...form, [name]: e.target.value })} fullWidth disabled={saving} {...props} />;

  if (!profile) return error ? <Alert severity="error">{error}</Alert> : <CircularProgress aria-label="Загрузка профиля" />;
  if (!profile.manageable_roles?.length) return <Alert severity="warning">Управление сотрудниками недоступно для вашей роли.</Alert>;
  return <Stack spacing={2}>
    <Typography variant="h5">Сотрудники</Typography>
    <Button variant="contained" onClick={() => open()}>Добавить сотрудника</Button>
    <TextField label="Поиск по имени, логину или телефону" value={search} onChange={(e) => setSearch(e.target.value)} />
    {message && <Alert severity="success" onClose={() => setMessage('')}>{message}</Alert>}
    {error && <Alert severity="error">{error}</Alert>}
    {loading ? <CircularProgress aria-label="Загрузка сотрудников" /> : rows.length === 0 ? <Typography>Сотрудники не найдены</Typography> : rows.map((user) => <Card key={user.id}><CardContent>
      <Typography variant="h6">{`${user.last_name} ${user.first_name}`.trim() || user.username}</Typography>
      <Typography color="text.secondary">{user.username}{user.phone ? ` · ${user.phone}` : ''}</Typography>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 1, flexWrap: 'wrap' }}>
        <Chip label={profile.manageable_roles.find((r) => r.value === user.role)?.label ?? ({ director: 'Директор', administrator: 'Администратор', accountant: 'Бухгалтер', designer: 'Проектировщик', support_manager: 'Менеджер по сопровождению', customer: 'Заказчик', project_manager: 'Руководитель проекта' }[user.role] || user.role)} size="small" />
        {!user.is_active && <Chip label="Вход отключён" size="small" />}
        {user.can_edit && <Button onClick={() => open(user)}>Редактировать</Button>}
      </Box>
    </CardContent></Card>)}
    <Dialog open={editing !== undefined} onClose={() => { if (!saving) setEditing(undefined); }} fullWidth maxWidth="sm">
      <Box component="form" onSubmit={save}>
        <DialogTitle>{editing ? 'Редактирование сотрудника' : 'Новый сотрудник'}</DialogTitle>
        <DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
          {formError && <Alert severity="error">{formError}</Alert>}
          {field('username', 'Логин', { required: true, autoComplete: 'off' })}
          {field('last_name', 'Фамилия')}{field('first_name', 'Имя')}
          {field('phone', 'Телефон', { type: 'tel' })}{field('email', 'Электронная почта', { type: 'email' })}
          <TextField select label="Должность" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} disabled={saving}>
            {profile.manageable_roles.map((role) => <MenuItem key={role.value} value={role.value}>{role.label}</MenuItem>)}
          </TextField>
          {field('password', editing ? 'Новый пароль (необязательно)' : 'Пароль', { required: !editing, type: 'password', autoComplete: 'new-password', helperText: editing ? 'Оставьте пустым, чтобы сохранить текущий пароль' : 'Передайте пароль сотруднику лично' })}
        </Stack></DialogContent>
        <DialogActions><Button disabled={saving} onClick={() => setEditing(undefined)}>Отмена</Button><Button type="submit" variant="contained" disabled={saving}>{saving ? 'Сохранение…' : 'Сохранить'}</Button></DialogActions>
      </Box>
    </Dialog>
  </Stack>;
}

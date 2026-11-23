import { useEffect, useState } from 'react';
import { Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from '@mui/material';
import { authApi, getApiErrorMessage, usersApi } from '../api';

const emptyForm = { username: '', first_name: '', last_name: '', phone: '', email: '', role: 'worker', password: '' };
const roleLabels = { director: 'Директор', administrator: 'Администратор', accountant: 'Бухгалтер', designer: 'Проектировщик', support_manager: 'Менеджер по сопровождению', customer: 'Заказчик', project_manager: 'Руководитель проекта', foreman: 'Мастер', worker: 'Монтажник' };

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
  const [archived, setArchived] = useState(false);
  const [archiveTarget, setArchiveTarget] = useState(null);
  const [archiveError, setArchiveError] = useState('');

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
      usersApi.list({ search, archived }).then(({ data }) => {
        if (active) { setRows(data.results ?? data); setError(''); }
      }).catch((e) => { if (active) setError(getApiErrorMessage(e)); })
        .finally(() => { if (active) setLoading(false); });
    }, 250);
    return () => { active = false; clearTimeout(timer); };
  }, [profile, search, archived]);

  const changeArchive = async () => {
    if (saving) return;
    setSaving(true); setArchiveError('');
    try {
      const restore = archiveTarget.status === 'dismissed';
      await usersApi.update(archiveTarget.id, { status: restore ? 'active' : 'dismissed' });
      setArchiveTarget(null);
      setMessage(restore ? 'Сотрудник восстановлен, вход разрешён' : 'Сотрудник перемещён в архив, вход отключён');
      setProfile((current) => ({ ...current }));
    } catch (e) { setArchiveError(getApiErrorMessage(e)); }
    finally { setSaving(false); }
  };

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
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} justifyContent="space-between" alignItems={{ sm: 'center' }}>
      <Typography variant="h5">Сотрудники</Typography>
      <Button variant="contained" onClick={() => open()}>Добавить сотрудника</Button>
    </Stack>
    <TextField label="Поиск по имени, логину или телефону" value={search} onChange={(e) => setSearch(e.target.value)} />
    <TextField select label="Список" value={archived ? 'archive' : 'current'} onChange={(e) => setArchived(e.target.value === 'archive')} sx={{ maxWidth: 300 }}>
      <MenuItem value="current">Действующие сотрудники</MenuItem>
      <MenuItem value="archive">Архив (уволенные)</MenuItem>
    </TextField>
    {message && <Alert severity="success" onClose={() => setMessage('')}>{message}</Alert>}
    {error && <Alert severity="error">{error}</Alert>}
    <Typography variant="body2" color="text.secondary">Найдено: {loading ? '…' : rows.length}. Изменения — через кнопку в строке сотрудника.</Typography>
    <TableContainer component={Paper} variant="outlined" tabIndex={0} aria-label="Список сотрудников, на узком экране прокручивается по горизонтали" sx={{ maxHeight: '65vh', borderRadius: 1 }}>
      <Table size="small" stickyHeader aria-label="Сотрудники" sx={{ minWidth: 1000, '& th, & td': { borderRight: '1px solid', borderRightColor: 'divider', py: 1 }, '& th': { fontWeight: 700, bgcolor: 'grey.100', whiteSpace: 'nowrap' } }}>
        <TableHead><TableRow>
          {['№', 'Фамилия', 'Имя', 'Логин', 'Должность', 'Телефон', 'Электронная почта', 'Вход', 'Действия'].map((label) => <TableCell key={label}>{label}</TableCell>)}
        </TableRow></TableHead>
        <TableBody>
          {loading ? <TableRow><TableCell colSpan={9} align="center"><CircularProgress size={24} aria-label="Загрузка сотрудников" /></TableCell></TableRow>
            : rows.length === 0 ? <TableRow><TableCell colSpan={9} align="center">Сотрудники не найдены</TableCell></TableRow>
              : rows.map((user, index) => <TableRow key={user.id} hover sx={{ bgcolor: index % 2 ? 'grey.50' : 'background.paper' }}>
                <TableCell>{index + 1}</TableCell>
                <TableCell>{user.last_name || '—'}</TableCell>
                <TableCell>{user.first_name || '—'}</TableCell>
                <TableCell>{user.username}</TableCell>
                <TableCell>{roleLabels[user.role] || user.role}</TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>{user.phone || '—'}</TableCell>
                <TableCell sx={{ overflowWrap: 'anywhere' }}>{user.email || '—'}</TableCell>
                <TableCell><Chip size="small" variant="outlined" color={user.is_active && user.status === 'active' ? 'success' : 'default'} label={user.is_active && user.status === 'active' ? 'Разрешён' : 'Отключён'} /></TableCell>
                <TableCell>{user.can_edit ? <Stack direction="row" spacing={1}>
                  <Button size="small" onClick={() => open(user)}>Редактировать</Button>
                  <Button size="small" color={archived ? 'primary' : 'warning'} onClick={() => { setArchiveError(''); setArchiveTarget(user); }}>{archived ? 'Восстановить' : 'В архив'}</Button>
                </Stack> : <Typography variant="caption" color="text.secondary">Только просмотр</Typography>}</TableCell>
              </TableRow>)}
        </TableBody>
      </Table>
    </TableContainer>
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
    <Dialog open={!!archiveTarget} onClose={() => { if (!saving) setArchiveTarget(null); }} fullWidth maxWidth="xs">
      <DialogTitle>{archiveTarget?.status === 'dismissed' ? 'Восстановить сотрудника?' : 'Переместить в архив?'}</DialogTitle>
      <DialogContent><Stack spacing={2}>
        <Typography>{archiveTarget && (`${archiveTarget.last_name} ${archiveTarget.first_name}`.trim() || archiveTarget.username)}</Typography>
        <Typography>{archiveTarget?.status === 'dismissed' ? 'Сотрудник вернётся в действующий список и сможет входить с прежним паролем.' : 'Вход будет отключён. История смен и выполненных работ сохранится.'}</Typography>
        {archiveError && <Alert severity="error">{archiveError}</Alert>}
      </Stack></DialogContent>
      <DialogActions><Button disabled={saving} onClick={() => setArchiveTarget(null)}>Отмена</Button><Button variant="contained" disabled={saving} onClick={changeArchive}>{saving ? 'Сохранение…' : archiveTarget?.status === 'dismissed' ? 'Восстановить' : 'В архив'}</Button></DialogActions>
    </Dialog>
  </Stack>;
}

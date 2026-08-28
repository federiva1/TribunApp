-- ============================================================================
-- Likes por RPC (endurecimiento de seguridad)
-- ============================================================================
-- Problema: la anon key tenía UPDATE(likes) sobre `formaciones`, así que
-- cualquiera con la clave pública podía hacer PATCH {likes: N} con N arbitrario
-- (inflar su formación al tope del ranking, o poner en 0 la de otro). El
-- anti-doble-like era solo localStorage, trivial de saltear.
--
-- Solución: el conteo de likes se DERIVA de una tabla (una fila por
-- (formación, dispositivo)), no de una columna editable. El toggle se hace por
-- una función SECURITY DEFINER que valida y cuenta server-side. Se revoca el
-- UPDATE directo del anon.
--
-- Correr una vez en Supabase → SQL Editor. Idempotente.
-- ============================================================================

-- 1. Una fila por (formación, dispositivo): la PK compuesta hace el like idempotente
create table if not exists public.formacion_likes (
  formacion_id uuid        not null references public.formaciones(id) on delete cascade,
  device_id    text        not null,
  created_at   timestamptz not null default now(),
  primary key (formacion_id, device_id)
);

-- RLS on y SIN políticas: nadie toca esta tabla directo; solo la función de abajo.
alter table public.formacion_likes enable row level security;

-- 2. Toggle atómico. Devuelve el conteo REAL (count de la tabla) y si quedó likeado.
create or replace function public.toggle_formacion_like(p_formacion_id uuid, p_device_id text)
returns table (likes int, liked boolean)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_exists boolean;
  v_likes  int;
begin
  -- device_id es un UUID de localStorage (dev_xxined...); validamos largo razonable
  if p_device_id is null or length(p_device_id) < 6 or length(p_device_id) > 64 then
    raise exception 'device_id invalido';
  end if;

  select exists(
    select 1 from formacion_likes
    where formacion_id = p_formacion_id and device_id = p_device_id
  ) into v_exists;

  if v_exists then
    delete from formacion_likes
      where formacion_id = p_formacion_id and device_id = p_device_id;
  else
    insert into formacion_likes(formacion_id, device_id)
      values (p_formacion_id, p_device_id)
      on conflict do nothing;
  end if;

  -- el conteo sale de la tabla (no de una columna manipulable)
  select count(*)::int into v_likes
    from formacion_likes where formacion_id = p_formacion_id;

  -- se mantiene formaciones.likes en sync para las lecturas/orden existentes
  update formaciones set likes = v_likes where id = p_formacion_id;

  return query select v_likes, (not v_exists);
end;
$$;

-- 3. Permisos: el anon SOLO ejecuta la función; se le saca el UPDATE directo.
--    (La app nunca escribe otras columnas por PATCH; el INSERT de votos sigue igual.)
revoke update on public.formaciones from anon;
grant execute on function public.toggle_formacion_like(uuid, text) to anon;

-- Nota: los `likes` históricos (puestos por el sistema viejo) quedan como están
-- hasta que alguien vuelva a togglear esa formación; a partir de ahí el conteo
-- refleja los likes reales por dispositivo. No hay pérdida de datos.

/** Keeps the last user-loaded IR file across reloads (IndexedDB: too big for localStorage). */

const DB = 'browsamp';
const STORE = 'files';
const KEY = 'userIr';

export interface StoredIr {
  name: string;
  bytes: ArrayBuffer;
}

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function tx<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest): Promise<T> {
  const db = await open();
  return new Promise<T>((resolve, reject) => {
    const req = fn(db.transaction(STORE, mode).objectStore(STORE));
    req.onsuccess = () => resolve(req.result as T);
    req.onerror = () => reject(req.error);
  }).finally(() => db.close());
}

export async function loadUserIr(): Promise<StoredIr | null> {
  try {
    return (await tx<StoredIr | undefined>('readonly', (s) => s.get(KEY))) ?? null;
  } catch {
    return null;
  }
}

export async function saveUserIr(ir: StoredIr): Promise<void> {
  try {
    await tx('readwrite', (s) => s.put(ir, KEY));
  } catch {
    // private mode etc.: the IR stays loaded for this session only
  }
}

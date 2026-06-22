import type { Http } from "./http";
import type { LaundryLoad, LaundryLoadCreate, LaundryLoadUpdate } from "./types";

const BASE = "/laundry/loads";

export interface LaundryClient {
  list(): Promise<LaundryLoad[]>;
  create(data: LaundryLoadCreate): Promise<LaundryLoad>;
  update(id: number, data: LaundryLoadUpdate): Promise<LaundryLoad>;
  remove(id: number): Promise<void>;
}

export function createLaundry(http: Http): LaundryClient {
  return {
    list() {
      return http.request<LaundryLoad[]>(BASE);
    },
    create(data) {
      return http.request<LaundryLoad>(BASE, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    update(id, data) {
      return http.request<LaundryLoad>(`${BASE}/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },
    remove(id) {
      return http.request<void>(`${BASE}/${id}`, { method: "DELETE" });
    },
  };
}

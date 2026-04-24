import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface CustomField {
  id: string;
  project_id: string;
  name: string;
  field_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  options: string[];
  is_required: boolean;
  position: number;
}

export interface CustomFieldValue {
  custom_field: CustomField;
  value: unknown;
}

@Injectable({ providedIn: 'root' })
export class CustomFieldsService {
  private readonly http = inject(HttpClient);

  listFields(projectId: string): Observable<CustomField[]> {
    return this.http.get<CustomField[]>(
      `${environment.apiBase}/api/projects/${projectId}/custom-fields/`,
    );
  }

  createField(projectId: string, data: {
    name: string;
    field_type: string;
    options?: string[];
    is_required?: boolean;
    position?: number;
  }): Observable<CustomField> {
    return this.http.post<CustomField>(
      `${environment.apiBase}/api/projects/${projectId}/custom-fields/`,
      data,
    );
  }

  updateField(projectId: string, fieldId: string, data: Partial<{
    name: string;
    options: string[];
    is_required: boolean;
    position: number;
  }>): Observable<CustomField> {
    return this.http.patch<CustomField>(
      `${environment.apiBase}/api/projects/${projectId}/custom-fields/${fieldId}/`,
      data,
    );
  }

  deleteField(projectId: string, fieldId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/projects/${projectId}/custom-fields/${fieldId}/`,
    );
  }

  getValues(taskId: string): Observable<CustomFieldValue[]> {
    return this.http.get<CustomFieldValue[]>(
      `${environment.apiBase}/api/tasks/${taskId}/custom-field-values/`,
    );
  }

  setValue(taskId: string, fieldId: string, value: unknown): Observable<CustomFieldValue> {
    return this.http.put<CustomFieldValue>(
      `${environment.apiBase}/api/tasks/${taskId}/custom-field-values/${fieldId}/`,
      { value },
    );
  }

  deleteValue(taskId: string, fieldId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/tasks/${taskId}/custom-field-values/${fieldId}/`,
    );
  }
}

import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ConfirmDialogService {
  confirm(message: string): Observable<boolean> {
    return new Observable(observer => {
      observer.next(window.confirm(message));
      observer.complete();
    });
  }
}

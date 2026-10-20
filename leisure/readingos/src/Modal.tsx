import * as Dialog from '@radix-ui/react-dialog';
import { useRef, type ReactNode, type FormEvent } from 'react';
export function Modal({title,children,onClose,onSubmit,wide=false}: {
  title:string; children:ReactNode; onClose:()=>void;
  onSubmit:(event:FormEvent<HTMLFormElement>)=>void; wide?:boolean;
}) {
  const previous=useRef(document.activeElement as HTMLElement|null);
  return <Dialog.Root open onOpenChange={open=>{if(!open)onClose();}}>
    <Dialog.Portal><Dialog.Overlay className="modal-backdrop" />
      <Dialog.Content asChild aria-describedby={undefined} onCloseAutoFocus={event=>{event.preventDefault();previous.current?.focus();}}>
        <form className={'modal '+(wide?'wide':'')} onSubmit={onSubmit}>
          <div className="section-heading"><Dialog.Title asChild><h2>{title}</h2></Dialog.Title>
            <Dialog.Close asChild><button type="button" aria-label="关闭对话框" title="关闭（Esc）">×</button></Dialog.Close>
          </div>{children}
        </form>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}

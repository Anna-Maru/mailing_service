from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from mailings.models import Mailing, MailingAttempt


class Command(BaseCommand):
    help = 'Отправка рассылок вручную через командную строку'

    def add_arguments(self, parser):
        parser.add_argument(
            'mailing_id',
            type=int,
            help='ID рассылки для отправки'
        )

    def handle(self, *args, **options):
        mailing_id = options['mailing_id']

        try:
            mailing = Mailing.objects.get(pk=mailing_id)
        except Mailing.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Рассылка с ID {mailing_id} не найдена')
            )
            return

        # Проверяем возможность отправки
        if not mailing.can_send():
            self.stdout.write(
                self.style.ERROR(
                    'Рассылка не может быть отправлена. '
                    'Текущее время должно быть между датой начала и окончания.'
                )
            )
            return

        # Получаем всех получателей
        recipients = mailing.recipients.all()

        if not recipients.exists():
            self.stdout.write(
                self.style.WARNING('У рассылки нет получателей!')
            )
            return

        self.stdout.write(f'Начинаем отправку рассылки #{mailing_id}')
        self.stdout.write(f'Сообщение: {mailing.message.subject}')
        self.stdout.write(f'Получателей: {recipients.count()}')
        self.stdout.write('-' * 50)

        success_count = 0
        failed_count = 0

        # Отправляем письма каждому получателю
        for client in recipients:
            try:
                send_mail(
                    subject=mailing.message.subject,
                    message=mailing.message.body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[client.email],
                    fail_silently=False,
                )

                # Создаем запись об успешной попытке
                MailingAttempt.objects.create(
                    mailing=mailing,
                    status=MailingAttempt.STATUS_SUCCESS,
                    server_response='Письмо успешно отправлено',
                    recipient_email=client.email
                )

                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Отправлено: {client.email}')
                )

            except Exception as e:
                # Создаем запись о неудачной попытке
                MailingAttempt.objects.create(
                    mailing=mailing,
                    status=MailingAttempt.STATUS_FAILED,
                    server_response=str(e),
                    recipient_email=client.email
                )

                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Ошибка {client.email}: {str(e)}')
                )

        # Обновляем статус рассылки
        mailing.update_status()

        # Итоговая статистика
        self.stdout.write('-' * 50)
        self.stdout.write(
            self.style.SUCCESS(f'Успешно отправлено: {success_count}')
        )
        if failed_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Не удалось отправить: {failed_count}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Рассылка завершена! Новый статус: {mailing.status}')
        )

FamilyHostsBlocker - GitHub Only
================================

هذه نسخة مخصصة للمرحلة الأولى فقط.

الهدف:
توليد الليستة النهائية على GitHub فقط، بدون أي تعديل على Windows وبدون لمس ملف hosts.

هذه النسخة لا تحتوي على:
- FamilyHostsBlocker.bat
- windows/FamilyHostsBlocker.ps1
- أي سكريبت يغير C:\Windows\System32\drivers\etc\hosts

المسار الحالي:
مصادر خارجية
-> GitHub Actions
-> scripts/update_hosts.py
-> familyblocker_domains.txt
-> familyblocker_hosts.txt
-> familyblocker_sources_report.tsv

الملفات المهمة:
- sources_enabled.txt
  روابط المصادر الخارجية المفعلة.

- sources_disabled.txt
  مصادر معطلة أو مرشحة لاحقًا.

- domains_manual.txt
  دومينات تضيفها يدويًا.

- domains_allowlist.txt
  دومينات لا تريد حظرها حتى لو جاءت من مصدر خارجي.

- scripts/update_hosts.py
  سكريبت توليد القوائم.

- .github/workflows/update_hosts.yml
  GitHub Actions لتحديث القوائم تلقائيًا.

- familyblocker_domains.txt
  القائمة النهائية للدومينات فقط.

- familyblocker_hosts.txt
  القائمة النهائية بصيغة hosts:
  0.0.0.0 example.com

- familyblocker_sources_report.tsv
  تقرير يوضح مصادر الدومينات.

خطوات الرفع:
1. أنشئ Repository جديد باسم:
   FamilyHostsBlocker

2. لا تضف README من GitHub.
   لا تضف .gitignore من GitHub.
   لا تضف License من GitHub.

3. ارفع محتويات هذا المجلد إلى GitHub.

4. افتح تبويب Actions.

5. شغّل:
   Update FamilyHostsBlocker lists

6. بعد نجاح التشغيل، تأكد أن الملفات التالية أصبحت ممتلئة:
   familyblocker_domains.txt
   familyblocker_hosts.txt
   familyblocker_sources_report.tsv

روابط الليستة بعد نجاح GitHub Actions:

دومينات فقط:
https://raw.githubusercontent.com/italesawy-droid/FamilyHostsBlocker/main/familyblocker_domains.txt

hosts format:
https://raw.githubusercontent.com/italesawy-droid/FamilyHostsBlocker/main/familyblocker_hosts.txt

ملاحظة:
لا تشغّل أي خطوة على Windows الآن.
المرحلة التالية لاحقًا ستكون بناء سكريبت منفصل يقوم بتحميل familyblocker_hosts.txt من GitHub وتطبيقه داخل ملف hosts مع backup و rollback.

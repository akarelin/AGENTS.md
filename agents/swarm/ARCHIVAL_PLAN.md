# Archival Plan

Mark items with ✅ to archive them.

## Tree Structure

```
📁 Root Items
├── ✅ WinServer/ → archive/scripts/winserver.saved/ (Scripts | SAVED)
├── ✅ chatgpt-history-export-to-md/ → archive/projects/etls.completed/chatgpt-export/ (Project | COMPLETED)  
├── ✅ new_py_project_init.sh → archive/misc/orphaned/ (Misc | ORPHANED)
├── ❗ synology_web_filebrowser.md → archive/legacy/docs/ (Legacy | SUPERSEDED)
├── 📁 _scratch/
│   ├── ✅ 2305 Atlona IP4K/ → archive/scripts/atlona-switch.saved/ (Scripts | SAVED)
│   ├── ✅ 2Do misc to Y2/ → archive/y2/discopub-zwjs/ (Y2 | ONGOING)
│   ├── ✅ 2Do yala to Y2/ → archive/y2/yala-components/ (Y2 | ONGOING)  
│   ├── 🗑️ AtlonaIP4K/ → DELETE (Empty directory)
│   ├── ✅ Hunter Duglas/ → archive/scripts/hunter-douglas.saved/ (Scripts | SAVED)
│   ├── ✅ Metaiot/ → archive/scripts/isy-automation.obsolete/ (Scripts | OBSOLETE)
│   └── 📦 Visualizer/ → MOVE TO CRAP/ETLs/graph-api-visualizer/ (For Graph API tasks)
├── ⬜ *.bak files → archive/misc/backups/manual-backups/ (Misc | BACKUP)
├── 📁 Services/
│   ├── 📁 ADG/
│   │   ├── ✅ Older/ → archive/services/adg/ (Services | SUPERSEDED)
│   │   └── ✅ 5.conf/ → archive/services/adg/ (Services | SUPERSEDED)
│   ├── ✅ hassios/older versions/ → archive/services/hassios/ (Services | SUPERSEDED)
│   ├── ✅ _Inactive/ → archive/services/inactive/ (Services | SUPERSEDED)
│   ├── ⬜ _Obsolete/ → archive/services/obsolete/ (Services | OBSOLETE)
│   ├── ⬜ _Unfinished/ → archive/services/unfinished/ (Services | ABANDONED)
│   ├── ⬜ _Yakimanka/ → archive/services/yakimanka/ (Services | SUPERSEDED)
│   ├── ⬜ bind/backup/ → archive/misc/backups/bind-backup/ (Misc | BACKUP)
│   ├── ⬜ SSL/Extra Scripts/ → archive/scripts/ssl-extra.saved/ (Scripts | SAVED)
│   └── 📁 nginx/
│       ├── ⬜ Old-Nginx-confgen.sh → archive/misc/orphaned/ (Misc | OBSOLETE)
│       └── ⬜ Overcomplicated/ → archive/experiments/nginx-overcomplicated/ (Experiments | ABANDONED)
├── 📁 _scripts/
│   └── ⬜ _Obsolete/ → archive/scripts/win11-obsolete.obsolete/ (Scripts | OBSOLETE)
├── 📁 Scripting/
│   ├── ⬜ ETLs/ → archive/etls/ran-etls/ (ETLs | COMPLETED)
│   ├── ⬜ Photometa/ → archive/etls/photometa/ (ETLs | COMPLETED)
│   ├── ⬜ SharePointing/ → archive/etls/sharepointing/ (ETLs | COMPLETED)
│   ├── ⬜ Suntrust/ → archive/etls/suntrust/ (ETLs | COMPLETED)
│   └── ⬜ crop_possum/ → archive/etls/crop-possum/ (ETLs | COMPLETED)
└── 📁 CRAP/ (External directory D:\Dev\CRAP)
    ├── ⬜ Autome/ → archive/etls/autome/ (ETLs | COMPLETED)
    ├── ⬜ CRM.dumper/ → archive/etls/crm-dumper/ (ETLs | ONGOING)
    ├── ⬜ CRM/ → archive/etls/crm/ (ETLs | ONGOING)
    ├── ⬜ Contactery/ → archive/etls/contactery/ (ETLs | ONGOING)
    ├── ⬜ ETLs/ → archive/etls/crap-etls/ (ETLs | ONGOING)
    ├── ⬜ MailStats/ → archive/scripts/mail-stats.saved/ (Scripts | SAVED)
    ├── ⬜ Mailstore/ → archive/etls/mailstore/ (ETLs | ONGOING)
    ├── ⬜ MessageDB/ → archive/etls/messagedb/ (ETLs | ONGOING)
    ├── ⬜ OneNote2md/ → archive/etls/onenote2md/ (ETLs | COMPLETED)
    ├── ⬜ Outlook2md/ → archive/etls/outlook2md/ (ETLs | COMPLETED)
    └── ⬜ Outlookery/ → archive/etls/outlookery/ (ETLs | COMPLETED)
```

## Status Legend
- ✅ **Ready to archive** (Reviewed and approved)
- ⬜ **Pending review** (Not yet reviewed)
- ❗ **Important - needs attention** (Special handling required)
- 🗑️ **DELETE** (Empty or unnecessary)
- 📦 **MOVE** (Relocate to different directory)

## Descriptions

### Already Marked for Archival
- **WinServer/**: Windows Server management scripts and configurations
- **chatgpt-history-export-to-md/**: ChatGPT history export tool
- **new_py_project_init.sh**: Single project initialization script

### Services Directory
- **ADG/Older/**: Old AdGuard configurations superseded by current setup
- **ADG/5.conf/**: AdGuard configs from 2021, replaced by newer versions
- **hassios/older versions/**: Old Home Assistant compose files
- **_Inactive/**: Inactive service configurations no longer in use
- **_Obsolete/**: Obsolete services (Azure2Local, Unifi-Voip, mongo_prune.js)
- **_Unfinished/**: Unfinished projects (Autopirate, Netdata, bind-webmin)
- **_Yakimanka/**: Location-specific old configs superseded by current setup
- **bind/backup/**: DNS bind backup files
- **SSL/Extra Scripts/**: Additional SSL management scripts with useful knowledge
- **nginx/Old-Nginx-confgen.sh**: Old nginx config generator, replaced
- **nginx/Overcomplicated/**: Overcomplicated nginx configurations, abandoned approach

### Scripting Directory  
- **ETLs/**: ETL scripts for data extraction and transformation (completed)
- **Photometa/**: Photo metadata extraction tools (completed)
- **SharePointing/**: SharePoint file inventory and extraction (completed)
- **Suntrust/**: SunTrust bank statement parsing and classification (completed)
- **crop_possum/**: Image cropping automation for possum photos (completed)

### Other Items
- **_scratch/**: Development scratch work and temporary experiments
- **_scripts/_Obsolete/**: Obsolete Windows 11 scripts
- ***.bak files**: Various .bak files throughout repository (manual backups)
- **synology_web_filebrowser.md**: Synology documentation superseded by current setup

## Instructions
1. Review each item and mark with ✅ if you want it archived
2. Items will be moved from Source to Destination with appropriate status  
3. Archive README will be updated with all archived items
4. **Project Consolidation Rule**: Keep all items related to the same service/project together in a single archive location
5. **Top-Level Categories**: Services, ETLs, and Y2 are ongoing efforts with archive/[category]/ structure
6. **Empty Folder Cleanup**: Delete all empty folders that are not submodules
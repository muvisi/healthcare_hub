from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.db import connections, transaction
from datetime import datetime, timedelta
import pytz

@transaction.atomic(using='external_mssql')
def alloc_commissions(request):
    """
    Allocate premiums from receipts to invoices safely in one transaction.
    Sends a styled email to Madison Group with all allocations and totals.
    Always sends an email even if nothing was allocated.
    """

    tz = pytz.timezone("Africa/Nairobi")
    today = datetime.now(tz).date()
    thisYr = today - timedelta(days=15)

    def crud(action, sql):
        with connections['external_mssql'].cursor() as cursor:
            cursor.execute(sql)
            if action == "R":
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            return "Successfully"

    def wh_log(msg):
        print(msg)

    # ===============================
    # GET RECEIPTS
    # ===============================
    if "invoice_no" in request.GET:
        invoNo = request.GET.get("invoice_no").strip()
        sqlreceipts = f"""
        select PREMIUM_RECEIPT.invoice_no,
               PREMIUM_RECEIPT.receipt_no,
               sum(PREMIUM_RECEIPT.receipt_amount) as receipt_amount
        from PREMIUM_RECEIPT
        where PREMIUM_RECEIPT.agent_id<>'54'
        and premium_receipt.invoice_no in ('{invoNo}')
        group by PREMIUM_RECEIPT.invoice_no, PREMIUM_RECEIPT.receipt_no
        """
    else:
        sqlreceipts = f"""
        select PREMIUM_RECEIPT.invoice_no,
               PREMIUM_RECEIPT.receipt_no,
               sum(PREMIUM_RECEIPT.receipt_amount) as receipt_amount
        from PREMIUM_RECEIPT
        where PREMIUM_RECEIPT.agent_id<>'54'
        and PREMIUM_RECEIPT.receipt_amount>0
        and PREMIUM_RECEIPT.receipt_date between '{thisYr}' and '{today}'
        group by PREMIUM_RECEIPT.invoice_no, PREMIUM_RECEIPT.receipt_no
        order by PREMIUM_RECEIPT.receipt_no desc
        """

    receipts = crud("R", sqlreceipts)
    allocations = []

    # ===============================
    # ALLOCATION LOGIC
    # ===============================
    for receipt in receipts:
        receipt_no = receipt["receipt_no"]
        invoice_no = receipt["invoice_no"]
        receipt_amount = float(receipt.get("receipt_amount") or 0)

        sqlAllocation = f"""
        with a as (
            select invoice_no,class,isnull(net_premium,0) as net_premium,
                   allocated,isnull(allocated_amt,0) as allocated_amt,
                   levied,receipt_no
            from premium_invoice_details_sammary
            where allocated is null
        ),
        b as (
            select invoice_no,class,allocated,
                   sum(isnull(allocated_amt,0)) as allocated_amt,
                   sum(isnull(levied,0)) as levied
            from premium_invoice_details_sammary
            where allocated=1
            group by invoice_no,class,allocated
        )
        select a.invoice_no,a.class,isnull(a.net_premium,0) as net_premium,
               b.allocated,isnull(b.allocated_amt,0) as allocated_amt,
               isnull(b.levied,0) as levied
        from a
        left outer join b
          on a.invoice_no=b.invoice_no and a.class=b.class
        where isnull(b.allocated_amt,0)<a.net_premium
        and a.invoice_no='{invoice_no}'
        """
        unAllocatedDebits = crud("R", sqlAllocation)
        if not unAllocatedDebits:
            continue

        for debit in unAllocatedDebits:
            class_ = debit["class"]
            net_premium = float(debit.get("net_premium") or 0)
            allocated_amt = float(debit.get("allocated_amt") or 0)

            # Calculate levies
            sqlLevy = f"""
            select invoice_no,
                   isnull(stamp_duty,0) sd,
                   isnull(tl,0) tl,
                   isnull(phcf,0) phcf
            from PREMIUM_INVOICE
            where invoice_no='{invoice_no}'
            """
            Levies = crud("R", sqlLevy)
            premLevies = sum(
                float(levy.get("sd") or 0) +
                float(levy.get("tl") or 0) +
                float(levy.get("phcf") or 0)
                for levy in Levies
            )

            sqLRctAllocation = f"""
            select invoice_no,
                   sum(isnull(allocated_amt,0)) as alloc_amt,
                   sum(isnull(levied,0)) as levy_amt,
                   (sum(isnull(allocated_amt,0))+sum(isnull(levied,0))) as T_allocated_amt
            from premium_invoice_details_sammary
            where allocated=1
            and invoice_no='{invoice_no}'
            and receipt_no='{receipt_no}'
            group by invoice_no
            """
            leviedAmounts = crud("R", sqLRctAllocation)
            alloc_amt_rec = t_allocate_rec = 0
            for la in leviedAmounts:
                alloc_amt_rec = float(la.get("alloc_amt") or 0)
                t_allocate_rec = float(la.get("T_allocated_amt") or 0)

            sqlLevyDeductions = f"""
            select sum(isnull(levied,0)) as levied
            from premium_invoice_details_sammary
            where allocated=1
            and invoice_no='{invoice_no}'
            """
            leviedDeductions = crud("R", sqlLevyDeductions)
            allLevy = sum(float(ld.get("levied") or 0) for ld in leviedDeductions)
            levied = round(premLevies - allLevy, 2) if premLevies != allLevy else 0

            if receipt_amount > levied:
                receipt_bal = receipt_amount - t_allocate_rec - levied
                unallocated_amt = net_premium - allocated_amt
                all_amt = min(receipt_bal, unallocated_amt)

                if all_amt > 0:
                    all_amt = round(min(all_amt, net_premium), 2)

                    # Insert allocation
                    crud("U", f"""
                    INSERT INTO premium_invoice_details_sammary
                    (id_key, invoice_no, class, net_premium,
                     allocated, allocated_amt, levied, receipt_no)
                    values(
                        (select max(id_key)+1 from premium_invoice_details_sammary),
                        '{invoice_no}','{class_}',NULL,1,
                        '{all_amt}','{levied}','{receipt_no}'
                    )
                    """)

                    # Update receipt as commission paid
                    crud("U", f"""
                    update PREMIUM_RECEIPT
                    set commis_paid='1'
                    where invoice_no='{invoice_no}'
                    and receipt_no='{receipt_no}'
                    """)

                    wh_log(f"{receipt_no} Allocated Successfully to {invoice_no}")

                    allocations.append({
                        "invoice_no": invoice_no,
                        "receipt_no": receipt_no,
                        "class": class_,
                        "allocated_amt": all_amt,
                        "levied": levied
                    })

    # ===============================
    # EMAIL REPORT
    # ===============================
    allocation_time = datetime.now().strftime("%d-%b-%Y %H:%M:%S")

    if allocations:
        table_rows = "".join(f"""
            <tr>
                <td>{a['invoice_no']}</td>
                <td>{a['receipt_no']}</td>
                <td>{a['class']}</td>
                <td style="text-align:right">{a['allocated_amt']:.2f}</td>
                <td style="text-align:right">{a['levied']:.2f}</td>
            </tr>
        """ for a in allocations)

        total_allocated = sum(a['allocated_amt'] for a in allocations)
        total_levied = sum(a['levied'] for a in allocations)

        totals_row = f"""
        <tr style="font-weight:bold; background-color:#e0e0e0;">
            <td colspan="3" style="text-align:center">TOTAL</td>
            <td style="text-align:right">{total_allocated:.2f}</td>
            <td style="text-align:right">{total_levied:.2f}</td>
        </tr>
        """
    else:
        table_rows = f"""
        <tr>
            <td colspan="5" style="text-align:center; font-style:italic;">No allocations done</td>
        </tr>
        """
        totals_row = ""

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color:#f5f5f5; padding:20px;">
            <!-- HEADER -->
            <div style="background-color:#4a4a4a; color:white; padding:10px; text-align:center;">
                <h2>Madison Group - Daily Commisions Allocation Report</h2>
                <p style="margin:0; font-size:14px;">Generated at: {allocation_time}</p>
            </div>

            <!-- BODY TABLE -->
            <div style="background-color:white; padding:15px; margin-top:10px; border-radius:5px;">
                <table border="1" cellpadding="5" cellspacing="0" width="100%" style="border-collapse:collapse;">
                    <thead style="background-color:#e0e0e0;">
                        <tr>
                            <th>Invoice No</th>
                            <th>Receipt No</th>
                            <th>Class</th>
                            <th>Allocated Amount</th>
                            <th>Levied</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                        {totals_row}
                    </tbody>
                </table>
            </div>

            <!-- FOOTER -->
            <div style="background-color:#d3d3d3; color:#333; padding:10px; margin-top:10px; border-radius:5px; text-align:center;">
                <p>Developer: Samuel Mwangangi</p>
                <p><em>Disclaimer: No defending systems, we make them work!</em></p>
            </div>
        </body>
    </html>
    """

    # Send email
    email = EmailMessage(
        subject="Madison Group - Daily Allocation Report",
        body=html_content,
        from_email="Madison Notifications <haisnotifications@madison.co.ke>",
        to=["samuel.mwangangi@madison.co.ke","mwangangimuvisi@gmail.com","paulyne.mukhanyi@madison.co.ke","ict@madison.co.ke"],
    )
    email.content_subtype = "html"
    email.send(fail_silently=False)

    return JsonResponse({"message": "Allocation completed", "allocations": allocations})

# from django.core.mail import EmailMessage
# from django.http import JsonResponse
# from django.db import connections, transaction
# # from django.utils.timezone import now
# from datetime import datetime
# from datetime import timedelta
# import pytz

# @transaction.atomic(using='external_mssql')
# def alloc_commissions(request):
#     """
#     Allocate premiums from receipts to invoices safely in one transaction.
#     Sends a styled email to Madison Group with all allocations and totals.
#     """

#     tz = pytz.timezone("Africa/Nairobi")
#     today = datetime.now().date()
#     thisYr = today - timedelta(days=150)

#     def crud(action, sql):
#         with connections['external_mssql'].cursor() as cursor:
#             cursor.execute(sql)
#             if action == "R":
#                 columns = [col[0] for col in cursor.description]
#                 return [dict(zip(columns, row)) for row in cursor.fetchall()]
#             return "Successfully"

#     def wh_log(msg):
#         print(msg)

#     # ===============================
#     # GET RECEIPTS
#     # ===============================
#     if "invoice_no" in request.GET:
#         invoNo = request.GET.get("invoice_no").strip()
#         sqlreceipts = f"""
#         select PREMIUM_RECEIPT.invoice_no,
#                PREMIUM_RECEIPT.receipt_no,
#                sum(PREMIUM_RECEIPT.receipt_amount) as receipt_amount
#         from PREMIUM_RECEIPT
#         where PREMIUM_RECEIPT.agent_id<>'54'
#         and premium_receipt.invoice_no in ('{invoNo}')
#         group by PREMIUM_RECEIPT.invoice_no, PREMIUM_RECEIPT.receipt_no
#         """
#     else:
#         sqlreceipts = f"""
#         select PREMIUM_RECEIPT.invoice_no,
#                PREMIUM_RECEIPT.receipt_no,
#                sum(PREMIUM_RECEIPT.receipt_amount) as receipt_amount
#         from PREMIUM_RECEIPT
#         where PREMIUM_RECEIPT.agent_id<>'54'
#         and PREMIUM_RECEIPT.receipt_amount>0
#         and PREMIUM_RECEIPT.receipt_date between '{thisYr}' and '{today}'
#         group by PREMIUM_RECEIPT.invoice_no, PREMIUM_RECEIPT.receipt_no
#         order by PREMIUM_RECEIPT.receipt_no desc
#         """

#     receipts = crud("R", sqlreceipts)
#     if not receipts:
#         return JsonResponse({"message": "No receipt(s) to allocate", "allocations": []})

#     allocations = []

#     # ===============================
#     # ALLOCATION LOGIC
#     # ===============================
#     for receipt in receipts:
#         receipt_no = receipt["receipt_no"]
#         invoice_no = receipt["invoice_no"]
#         receipt_amount = float(receipt.get("receipt_amount") or 0)

#         sqlAllocation = f"""
#         with a as (
#             select invoice_no,class,isnull(net_premium,0) as net_premium,
#                    allocated,isnull(allocated_amt,0) as allocated_amt,
#                    levied,receipt_no
#             from premium_invoice_details_sammary
#             where allocated is null
#         ),
#         b as (
#             select invoice_no,class,allocated,
#                    sum(isnull(allocated_amt,0)) as allocated_amt,
#                    sum(isnull(levied,0)) as levied
#             from premium_invoice_details_sammary
#             where allocated=1
#             group by invoice_no,class,allocated
#         )
#         select a.invoice_no,a.class,isnull(a.net_premium,0) as net_premium,
#                b.allocated,isnull(b.allocated_amt,0) as allocated_amt,
#                isnull(b.levied,0) as levied
#         from a
#         left outer join b
#           on a.invoice_no=b.invoice_no and a.class=b.class
#         where isnull(b.allocated_amt,0)<a.net_premium
#         and a.invoice_no='{invoice_no}'
#         """
#         unAllocatedDebits = crud("R", sqlAllocation)
#         if not unAllocatedDebits:
#             continue

#         for debit in unAllocatedDebits:
#             class_ = debit["class"]
#             net_premium = float(debit.get("net_premium") or 0)
#             allocated_amt = float(debit.get("allocated_amt") or 0)

#             # Calculate levies
#             sqlLevy = f"""
#             select invoice_no,
#                    isnull(stamp_duty,0) sd,
#                    isnull(tl,0) tl,
#                    isnull(phcf,0) phcf
#             from PREMIUM_INVOICE
#             where invoice_no='{invoice_no}'
#             """
#             Levies = crud("R", sqlLevy)
#             premLevies = sum(
#                 float(levy.get("sd") or 0) +
#                 float(levy.get("tl") or 0) +
#                 float(levy.get("phcf") or 0)
#                 for levy in Levies
#             )

#             # Levied allocations for this receipt
#             sqLRctAllocation = f"""
#             select invoice_no,
#                    sum(isnull(allocated_amt,0)) as alloc_amt,
#                    sum(isnull(levied,0)) as levy_amt,
#                    (sum(isnull(allocated_amt,0))+sum(isnull(levied,0))) as T_allocated_amt
#             from premium_invoice_details_sammary
#             where allocated=1
#             and invoice_no='{invoice_no}'
#             and receipt_no='{receipt_no}'
#             group by invoice_no
#             """
#             leviedAmounts = crud("R", sqLRctAllocation)
#             alloc_amt_rec = t_allocate_rec = 0
#             for la in leviedAmounts:
#                 alloc_amt_rec = float(la.get("alloc_amt") or 0)
#                 t_allocate_rec = float(la.get("T_allocated_amt") or 0)

#             # Total levied deductions
#             sqlLevyDeductions = f"""
#             select sum(isnull(levied,0)) as levied
#             from premium_invoice_details_sammary
#             where allocated=1
#             and invoice_no='{invoice_no}'
#             """
#             leviedDeductions = crud("R", sqlLevyDeductions)
#             allLevy = sum(float(ld.get("levied") or 0) for ld in leviedDeductions)
#             levied = round(premLevies - allLevy, 2) if premLevies != allLevy else 0

#             if receipt_amount > levied:
#                 receipt_bal = receipt_amount - t_allocate_rec - levied
#                 unallocated_amt = net_premium - allocated_amt
#                 all_amt = min(receipt_bal, unallocated_amt)

#                 if all_amt > 0:
#                     all_amt = round(min(all_amt, net_premium), 2)

#                     # Insert allocation
#                     crud("U", f"""
#                     INSERT INTO premium_invoice_details_sammary
#                     (id_key, invoice_no, class, net_premium,
#                      allocated, allocated_amt, levied, receipt_no)
#                     values(
#                         (select max(id_key)+1 from premium_invoice_details_sammary),
#                         '{invoice_no}','{class_}',NULL,1,
#                         '{all_amt}','{levied}','{receipt_no}'
#                     )
#                     """)

#                     # Update receipt as commission paid
#                     crud("U", f"""
#                     update PREMIUM_RECEIPT
#                     set commis_paid='1'
#                     where invoice_no='{invoice_no}'
#                     and receipt_no='{receipt_no}'
#                     """)

#                     wh_log(f"{receipt_no} Allocated Successfully to {invoice_no}")

#                     allocations.append({
#                         "invoice_no": invoice_no,
#                         "receipt_no": receipt_no,
#                         "class": class_,
#                         "allocated_amt": all_amt,
#                         "levied": levied
#                     })

#     # ===============================
#     # SEND EMAIL WITH REPORT
#     # ===============================
#     if allocations:
#         total_allocated = sum(a['allocated_amt'] for a in allocations)
#         total_levied = sum(a['levied'] for a in allocations)

#         table_rows = "".join(f"""
#             <tr>
#                 <td>{alloc['invoice_no']}</td>
#                 <td>{alloc['receipt_no']}</td>
#                 <td>{alloc['class']}</td>
#                 <td style="text-align:right">{alloc['allocated_amt']:.2f}</td>
#                 <td style="text-align:right">{alloc['levied']:.2f}</td>
#             </tr>
#         """ for alloc in allocations)

#         # Totals row
#         totals_row = f"""
#         <tr style="font-weight:bold; background-color:#e0e0e0;">
#             <td colspan="3" style="text-align:center">TOTAL</td>
#             <td style="text-align:right">{total_allocated:.2f}</td>
#             <td style="text-align:right">{total_levied:.2f}</td>
#         </tr>
#         """

#         allocation_time = datetime.now().strftime("%d-%b-%Y %H:%M:%S")

#         html_content = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif; background-color:#f5f5f5; padding:20px;">
#                 <!-- HEADER -->
#                 <div style="background-color:#4a4a4a; color:white; padding:10px; text-align:center;">
#                     <h2>Madison Group - Daily Commisions Allocation Report</h2>
#                     <p style="margin:0; font-size:14px;">Allocated at: {allocation_time}</p>
#                 </div>

#                 <!-- BODY TABLE -->
#                 <div style="background-color:white; padding:15px; margin-top:10px; border-radius:5px;">
#                     <table border="1" cellpadding="5" cellspacing="0" width="100%" style="border-collapse:collapse;">
#                         <thead style="background-color:#e0e0e0;">
#                             <tr>
#                                 <th>Invoice No</th>
#                                 <th>Receipt No</th>
#                                 <th>Class</th>
#                                 <th>Allocated Amount</th>
#                                 <th>Levied</th>
#                             </tr>
#                         </thead>
#                         <tbody>
#                             {table_rows}
#                             {totals_row}
#                         </tbody>
#                     </table>
#                 </div>

#                 <!-- FOOTER -->
#                 <div style="background-color:#d3d3d3; color:#333; padding:10px; margin-top:10px; border-radius:5px; text-align:center;">
#                     <p>Developed by Samuel Mwangangi</p>
#                     <p><em>ICT: No defending systems, we make them work!</em></p>
#                 </div>
#             </body>
#         </html>
#         """

#         email = EmailMessage(
#             subject="Madison Group - Allocation Report",
#             body=html_content,
#             from_email="Madison Notifications <haisnotifications@madison.co.ke>",
#             to=["info@madisongroup.com"],
#         )
#         email.content_subtype = "html"
#         email.send(fail_silently=False)

#     return JsonResponse({"message": "Allocation completed", "allocations": allocations})




# from django.core.mail import EmailMessage
# from django.http import JsonResponse
# from django.db import connections, transaction
# from django.utils.timezone import now
# from datetime import timedelta
# import pytz

# @transaction.atomic(using='external_mssql')
# def alloc_commissions(request):
#     """
#     Allocate premiums from receipts to invoices safely in one transaction.
#     Sends a styled email to Madison Group with all allocations.
#     """

#     tz = pytz.timezone("Africa/Nairobi")
#     today = now().astimezone(tz).date()
#     thisYr = today - timedelta(days=90)

#     def crud(action, sql):
#         with connections['external_mssql'].cursor() as cursor:
#             cursor.execute(sql)
#             if action == "R":
#                 columns = [col[0] for col in cursor.description]
#                 return [dict(zip(columns, row)) for row in cursor.fetchall()]
#             return "Successfully"

#     def wh_log(msg):
#         print(msg)

#     # ===============================
#     # GET RECEIPTS
#     # ===============================
#     if "invoice_no" in request.GET:
#         invoNo = request.GET.get("invoice_no").strip()
#         sqlreceipts = f"""
#         select PREMIUM_RECEIPT.invoice_no,
#                PREMIUM_RECEIPT.receipt_no,
#                sum(PREMIUM_RECEIPT.receipt_amount) as receipt_amount
#         from PREMIUM_RECEIPT
#         where PREMIUM_RECEIPT.agent_id<>'54'
#         and premium_receipt.invoice_no in ('{invoNo}')
#         group by PREMIUM_RECEIPT.invoice_no, PREMIUM_RECEIPT.receipt_no
#         """
#     else:
#         sqlreceipts = f"""
#         select PREMIUM_RECEIPT.invoice_no,
#                PREMIUM_RECEIPT.receipt_no,
#                sum(PREMIUM_RECEIPT.receipt_amount) as receipt_amount
#         from PREMIUM_RECEIPT
#         where PREMIUM_RECEIPT.agent_id<>'54'
#         and PREMIUM_RECEIPT.receipt_amount>0
#         and PREMIUM_RECEIPT.receipt_date between '{thisYr}' and '{today}'
#         group by PREMIUM_RECEIPT.invoice_no, PREMIUM_RECEIPT.receipt_no
#         order by PREMIUM_RECEIPT.receipt_no desc
#         """

#     receipts = crud("R", sqlreceipts)
#     if not receipts:
#         return JsonResponse({"message": "No receipt(s) to allocate", "allocations": []})

#     allocations = []

#     # ===============================
#     # ALLOCATION LOGIC
#     # ===============================
#     for receipt in receipts:
#         receipt_no = receipt["receipt_no"]
#         invoice_no = receipt["invoice_no"]
#         receipt_amount = float(receipt.get("receipt_amount") or 0)

#         sqlAllocation = f"""
#         with a as (
#             select invoice_no,class,isnull(net_premium,0) as net_premium,
#                    allocated,isnull(allocated_amt,0) as allocated_amt,
#                    levied,receipt_no
#             from premium_invoice_details_sammary
#             where allocated is null
#         ),
#         b as (
#             select invoice_no,class,allocated,
#                    sum(isnull(allocated_amt,0)) as allocated_amt,
#                    sum(isnull(levied,0)) as levied
#             from premium_invoice_details_sammary
#             where allocated=1
#             group by invoice_no,class,allocated
#         )
#         select a.invoice_no,a.class,isnull(a.net_premium,0) as net_premium,
#                b.allocated,isnull(b.allocated_amt,0) as allocated_amt,
#                isnull(b.levied,0) as levied
#         from a
#         left outer join b
#           on a.invoice_no=b.invoice_no and a.class=b.class
#         where isnull(b.allocated_amt,0)<a.net_premium
#         and a.invoice_no='{invoice_no}'
#         """
#         unAllocatedDebits = crud("R", sqlAllocation)
#         if not unAllocatedDebits:
#             continue

#         for debit in unAllocatedDebits:
#             class_ = debit["class"]
#             net_premium = float(debit.get("net_premium") or 0)
#             allocated_amt = float(debit.get("allocated_amt") or 0)

#             # Calculate levies
#             sqlLevy = f"""
#             select invoice_no,
#                    isnull(stamp_duty,0) sd,
#                    isnull(tl,0) tl,
#                    isnull(phcf,0) phcf
#             from PREMIUM_INVOICE
#             where invoice_no='{invoice_no}'
#             """
#             Levies = crud("R", sqlLevy)
#             premLevies = sum(
#                 float(levy.get("sd") or 0) +
#                 float(levy.get("tl") or 0) +
#                 float(levy.get("phcf") or 0)
#                 for levy in Levies
#             )

#             # Levied allocations for this receipt
#             sqLRctAllocation = f"""
#             select invoice_no,
#                    sum(isnull(allocated_amt,0)) as alloc_amt,
#                    sum(isnull(levied,0)) as levy_amt,
#                    (sum(isnull(allocated_amt,0))+sum(isnull(levied,0))) as T_allocated_amt
#             from premium_invoice_details_sammary
#             where allocated=1
#             and invoice_no='{invoice_no}'
#             and receipt_no='{receipt_no}'
#             group by invoice_no
#             """
#             leviedAmounts = crud("R", sqLRctAllocation)
#             alloc_amt_rec = t_allocate_rec = 0
#             for la in leviedAmounts:
#                 alloc_amt_rec = float(la.get("alloc_amt") or 0)
#                 t_allocate_rec = float(la.get("T_allocated_amt") or 0)

#             # Total levied deductions
#             sqlLevyDeductions = f"""
#             select sum(isnull(levied,0)) as levied
#             from premium_invoice_details_sammary
#             where allocated=1
#             and invoice_no='{invoice_no}'
#             """
#             leviedDeductions = crud("R", sqlLevyDeductions)
#             allLevy = sum(float(ld.get("levied") or 0) for ld in leviedDeductions)
#             levied = round(premLevies - allLevy, 2) if premLevies != allLevy else 0

#             if receipt_amount > levied:
#                 receipt_bal = receipt_amount - t_allocate_rec - levied
#                 unallocated_amt = net_premium - allocated_amt
#                 all_amt = min(receipt_bal, unallocated_amt)

#                 if all_amt > 0:
#                     all_amt = round(min(all_amt, net_premium), 2)

#                     # Insert allocation
#                     crud("U", f"""
#                     INSERT INTO premium_invoice_details_sammary
#                     (id_key, invoice_no, class, net_premium,
#                      allocated, allocated_amt, levied, receipt_no)
#                     values(
#                         (select max(id_key)+1 from premium_invoice_details_sammary),
#                         '{invoice_no}','{class_}',NULL,1,
#                         '{all_amt}','{levied}','{receipt_no}'
#                     )
#                     """)

#                     # Update receipt as commission paid
#                     crud("U", f"""
#                     update PREMIUM_RECEIPT
#                     set commis_paid='1'
#                     where invoice_no='{invoice_no}'
#                     and receipt_no='{receipt_no}'
#                     """)

#                     wh_log(f"{receipt_no} Allocated Successfully to {invoice_no}")

#                     allocations.append({
#                         "invoice_no": invoice_no,
#                         "receipt_no": receipt_no,
#                         "class": class_,
#                         "allocated_amt": all_amt,
#                         "levied": levied
#                     })

#     # ===============================
#     # SEND EMAIL
#     # ===============================
#     if allocations:
#         table_rows = "".join(f"""
#             <tr>
#                 <td>{alloc['invoice_no']}</td>
#                 <td>{alloc['receipt_no']}</td>
#                 <td>{alloc['class']}</td>
#                 <td style="text-align:right">{alloc['allocated_amt']:.2f}</td>
#                 <td style="text-align:right">{alloc['levied']:.2f}</td>
#             </tr>
#         """ for alloc in allocations)

#         html_content = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif; background-color:#f5f5f5; padding:20px;">
#                 <!-- HEADER -->
#                 <div style="background-color:#4a4a4a; color:white; padding:10px; text-align:center;">
#                     <h2>Madison Group - Allocation Report</h2>
#                 </div>

#                 <!-- BODY TABLE -->
#                 <div style="background-color:white; padding:15px; margin-top:10px; border-radius:5px;">
#                     <table border="1" cellpadding="5" cellspacing="0" width="100%" style="border-collapse:collapse;">
#                         <thead style="background-color:#e0e0e0;">
#                             <tr>
#                                 <th>Invoice No</th>
#                                 <th>Receipt No</th>
#                                 <th>Class</th>
#                                 <th>Allocated Amount</th>
#                                 <th>Levied</th>
#                             </tr>
#                         </thead>
#                         <tbody>
#                             {table_rows}
#                         </tbody>
#                     </table>
#                 </div>

#                 <!-- FOOTER -->
#                 <div style="background-color:#d3d3d3; color:#333; padding:10px; margin-top:10px; border-radius:5px; text-align:center;">
#                     <p>Developer:Eng. Samuel Mwangangi</p>
#                     <p><em>Disclaimer: No defending systems, we make them work!</em></p>
#                 </div>
#             </body>
#         </html>
#         """

        
#         email = EmailMessage(
#                 subject="Madison Group - Allocation Report",
#                 body=html_content,
#                 from_email="Madison Notifications <haisnotifications@madison.co.ke>",
#                 to=["samuel.mwangangi@madison.co.ke","mwangangimuvisi@gmail.com"],
# )
#         email.content_subtype = "html"
#         email.send(fail_silently=False)

#     return JsonResponse({"message": "Allocation completed", "allocations": allocations})





# # from django.shortcuts import render

# # # Create your views here.
# # from django.http import HttpResponse
# # from django.db import connections, transaction
# # from django.utils.timezone import now
# # from datetime import timedelta
# # import pytz


# # @transaction.atomic(using='external_mssql')
# # def alloc_commissions(request):
# #     """
# #     Allocate premiums from receipts to invoices safely in one transaction.
# #     Fully wrapped for external MSSQL connection.
# #     """

# #     # ===============================
# #     # BASE URL / PATH HANDLING
# #     # ===============================
# #     base_dir1 = request.get_full_path()
# #     base_dir = base_dir1.split('?')[0]

# #     if "Hais/" in base_dir:
# #         result = base_dir.split("Hais/")
# #         folda = result[1].split("/")
# #         base_folder = "../" if len(folda) > 1 else ""
# #     else:
# #         base_folder = ""

# #     baseer_fold = base_folder  # unchanged

# #     # ===============================
# #     # TIMEZONE & DATES
# #     # ===============================
# #     tz = pytz.timezone("Africa/Nairobi")
# #     today = now().astimezone(tz).date()
# #     thisYr = today - timedelta(days=150)

# #     # ===============================
# #     # DB HELPER
# #     # ===============================
# #     def crud(action, sql):
# #         with connections['external_mssql'].cursor() as cursor:
# #             cursor.execute(sql)

# #             if action == "R":
# #                 columns = [col[0] for col in cursor.description]
# #                 return [dict(zip(columns, row)) for row in cursor.fetchall()]

# #             return "Successfully"

# #     def wh_log(msg):
# #         # Replace with proper logging if needed
# #         print(msg)

# #     # ===============================
# #     # GET RECEIPTS
# #     # ===============================
# #     if "invoice_no" in request.GET:
# #         invoNo = request.GET.get("invoice_no").strip()
# #         sqlreceipts = f"""
# #         select PREMIUM_RECEIPT.invoice_no,
# #                PREMIUM_RECEIPT.receipt_no,
# #                sum(PREMIUM_RECEIPT.receipt_amount) as receipt_amount
# #         from PREMIUM_RECEIPT
# #         where PREMIUM_RECEIPT.agent_id<>'54'
# #         and premium_receipt.invoice_no in ('{invoNo}')
# #         group by PREMIUM_RECEIPT.invoice_no, PREMIUM_RECEIPT.receipt_no
# #         """
# #     else:
# #         sqlreceipts = f"""
# #         select PREMIUM_RECEIPT.invoice_no,
# #                PREMIUM_RECEIPT.receipt_no,
# #                sum(PREMIUM_RECEIPT.receipt_amount) as receipt_amount
# #         from PREMIUM_RECEIPT
# #         where PREMIUM_RECEIPT.agent_id<>'54'
# #         and PREMIUM_RECEIPT.receipt_amount>0
# #         and PREMIUM_RECEIPT.receipt_date between '{thisYr}' and '{today}'
# #         group by PREMIUM_RECEIPT.invoice_no, PREMIUM_RECEIPT.receipt_no
# #         order by PREMIUM_RECEIPT.receipt_no desc
# #         """

# #     receipts = crud("R", sqlreceipts)

# #     # ===============================
# #     # MAIN ALLOCATION LOGIC
# #     # ===============================
# #     if not receipts:
# #         return HttpResponse("No receipt(s) to allocate")

# #     for receipt in receipts:
# #         print(receipt)
# #         receipt_no = receipt["receipt_no"]
# #         invoice_no = receipt["invoice_no"]
# #         receipt_amount = float(receipt["receipt_amount"])

# #         # Fetch unallocated invoice details
# #         sqlAllocation = f"""
# #         with a as (
# #             select invoice_no,class,isnull(net_premium,0) as net_premium,
# #                    allocated,isnull(allocated_amt,0) as allocated_amt,
# #                    levied,receipt_no
# #             from premium_invoice_details_sammary
# #             where allocated is null
# #         ),
# #         b as (
# #             select invoice_no,class,allocated,
# #                    sum(isnull(allocated_amt,0)) as allocated_amt,
# #                    sum(isnull(levied,0)) as levied
# #             from premium_invoice_details_sammary
# #             where allocated=1
# #             group by invoice_no,class,allocated
# #         )
# #         select a.invoice_no,a.class,isnull(a.net_premium,0) as net_premium,
# #                b.allocated,isnull(b.allocated_amt,0) as allocated_amt,
# #                isnull(b.levied,0) as levied
# #         from a
# #         left outer join b
# #           on a.invoice_no=b.invoice_no and a.class=b.class
# #         where isnull(b.allocated_amt,0)<a.net_premium
# #         and a.invoice_no='{invoice_no}'
# #         """

# #         unAllocatedDebits = crud("R", sqlAllocation)

# #         if not unAllocatedDebits:
# #             continue

# #         for debit in unAllocatedDebits:

# #             class_ = debit["class"]
# #             net_premium = float(debit["net_premium"])
# #             allocated_amt = float(debit["allocated_amt"])

# #             # Calculate levies
# #             sqlLevy = f"""
# #             select invoice_no,
# #                    isnull(stamp_duty,0) sd,
# #                    isnull(tl,0) tl,
# #                    isnull(phcf,0) phcf
# #             from PREMIUM_INVOICE
# #             where invoice_no='{invoice_no}'
# #             """
# #             Levies = crud("R", sqlLevy)

# #             premLevies = sum(float(levy["sd"]) + float(levy["tl"]) + float(levy["phcf"]) for levy in Levies)

# #             # Levied allocations for this receipt
# #             sqLRctAllocation = f"""
# #             select invoice_no,
# #                    sum(isnull(allocated_amt,0)) as alloc_amt,
# #                    sum(isnull(levied,0)) as levy_amt,
# #                    (sum(isnull(allocated_amt,0))+sum(isnull(levied,0))) as T_allocated_amt
# #             from premium_invoice_details_sammary
# #             where allocated=1
# #             and invoice_no='{invoice_no}'
# #             and receipt_no='{receipt_no}'
# #             group by invoice_no
# #             """
# #             leviedAmounts = crud("R", sqLRctAllocation)

# #             alloc_amt_rec = t_allocate_rec = 0
# #             for la in leviedAmounts:
# #                 alloc_amt_rec = float(la["alloc_amt"])
# #                 t_allocate_rec = float(la["T_allocated_amt"])

# #             # Total levied deductions
# #             sqlLevyDeductions = f"""
# #             select sum(isnull(levied,0)) as levied
# #             from premium_invoice_details_sammary
# #             where allocated=1
# #             and invoice_no='{invoice_no}'
# #             """
# #             leviedDeductions = crud("R", sqlLevyDeductions)

# #             allLevy = sum(float(ld["levied"]) for ld in leviedDeductions)

# #             levied = round(premLevies - allLevy, 2) if premLevies != allLevy else 0

# #             if receipt_amount > levied:
# #                 receipt_bal = receipt_amount - t_allocate_rec - levied
# #                 unallocated_amt = net_premium - allocated_amt
# #                 all_amt = min(receipt_bal, unallocated_amt)

# #                 if all_amt > 0:
# #                     all_amt = round(min(all_amt, net_premium), 2)

# #                     # Insert allocation
# #                     crud("U", f"""
# #                     INSERT INTO premium_invoice_details_sammary
# #                     (id_key, invoice_no, class, net_premium,
# #                      allocated, allocated_amt, levied, receipt_no)
# #                     values(
# #                         (select max(id_key)+1 from premium_invoice_details_sammary),
# #                         '{invoice_no}','{class_}',NULL,1,
# #                         '{all_amt}','{levied}','{receipt_no}'
# #                     )
# #                     """)

# #                     # Update receipt as commission paid
# #                     crud("U", f"""
# #                     update PREMIUM_RECEIPT
# #                     set commis_paid='1'
# #                     where invoice_no='{invoice_no}'
# #                     and receipt_no='{receipt_no}'
# #                     """)

# #                     wh_log(f"{receipt_no} Allocated Successfully to {invoice_no}")

# #     return HttpResponse("Allocation completed")


# from django.shortcuts import render
# from django.http import HttpResponse
# from django.db import connections, transaction
# from django.utils.timezone import now
# from datetime import timedelta
# import pytz


# @transaction.atomic(using='external_mssql')
# def alloc_commissions(request):
#     """
#     Allocate premiums from receipts to invoices safely in one transaction.
#     Fully wrapped for external MSSQL connection.
#     """

#     # ===============================
#     # BASE URL / PATH HANDLING
#     # ===============================
#     base_dir1 = request.get_full_path()
#     base_dir = base_dir1.split('?')[0]

#     if "Hais/" in base_dir:
#         result = base_dir.split("Hais/")
#         folda = result[1].split("/")
#         base_folder = "../" if len(folda) > 1 else ""
#     else:
#         base_folder = ""

#     baseer_fold = base_folder  # unchanged

#     # ===============================
#     # TIMEZONE & DATES
#     # ===============================
#     tz = pytz.timezone("Africa/Nairobi")
#     today = now().astimezone(tz).date()
#     thisYr = today - timedelta(days=150)

#     # ===============================
#     # DB HELPER
#     # ===============================
#     def crud(action, sql):
#         with connections['external_mssql'].cursor() as cursor:
#             cursor.execute(sql)

#             if action == "R":
#                 columns = [col[0] for col in cursor.description]
#                 return [dict(zip(columns, row)) for row in cursor.fetchall()]

#             return "Successfully"

#     def wh_log(msg):
#         # Replace with proper logging if needed
#         print(msg)

#     # ===============================
#     # GET RECEIPTS
#     # ===============================
#     if "invoice_no" in request.GET:
#         invoNo = request.GET.get("invoice_no").strip()
#         sqlreceipts = f"""
#         select PREMIUM_RECEIPT.invoice_no,
#                PREMIUM_RECEIPT.receipt_no,
#                sum(PREMIUM_RECEIPT.receipt_amount) as receipt_amount
#         from PREMIUM_RECEIPT
#         where PREMIUM_RECEIPT.agent_id<>'54'
#         and premium_receipt.invoice_no in ('{invoNo}')
#         group by PREMIUM_RECEIPT.invoice_no, PREMIUM_RECEIPT.receipt_no
#         """
#     else:
#         sqlreceipts = f"""
#         select PREMIUM_RECEIPT.invoice_no,
#                PREMIUM_RECEIPT.receipt_no,
#                sum(PREMIUM_RECEIPT.receipt_amount) as receipt_amount
#         from PREMIUM_RECEIPT
#         where PREMIUM_RECEIPT.agent_id<>'54'
#         and PREMIUM_RECEIPT.receipt_amount>0
#         and PREMIUM_RECEIPT.receipt_date between '{thisYr}' and '{today}'
#         group by PREMIUM_RECEIPT.invoice_no, PREMIUM_RECEIPT.receipt_no
#         order by PREMIUM_RECEIPT.receipt_no desc
#         """

#     receipts = crud("R", sqlreceipts)

#     # ===============================
#     # MAIN ALLOCATION LOGIC
#     # ===============================
#     if not receipts:
#         return HttpResponse("No receipt(s) to allocate")

#     for receipt in receipts:
#         print(receipt)
#         receipt_no = receipt["receipt_no"]
#         invoice_no = receipt["invoice_no"]
#         receipt_amount = float(receipt["receipt_amount"] or 0)

#         # Fetch unallocated invoice details
#         sqlAllocation = f"""
#         with a as (
#             select invoice_no,class,isnull(net_premium,0) as net_premium,
#                    allocated,isnull(allocated_amt,0) as allocated_amt,
#                    levied,receipt_no
#             from premium_invoice_details_sammary
#             where allocated is null
#         ),
#         b as (
#             select invoice_no,class,allocated,
#                    sum(isnull(allocated_amt,0)) as allocated_amt,
#                    sum(isnull(levied,0)) as levied
#             from premium_invoice_details_sammary
#             where allocated=1
#             group by invoice_no,class,allocated
#         )
#         select a.invoice_no,a.class,isnull(a.net_premium,0) as net_premium,
#                b.allocated,isnull(b.allocated_amt,0) as allocated_amt,
#                isnull(b.levied,0) as levied
#         from a
#         left outer join b
#           on a.invoice_no=b.invoice_no and a.class=b.class
#         where isnull(b.allocated_amt,0)<a.net_premium
#         and a.invoice_no='{invoice_no}'
#         """

#         unAllocatedDebits = crud("R", sqlAllocation)

#         if not unAllocatedDebits:
#             continue

#         for debit in unAllocatedDebits:

#             class_ = debit["class"]
#             net_premium = float(debit["net_premium"] or 0)
#             allocated_amt = float(debit["allocated_amt"] or 0)

#             # Calculate levies
#             sqlLevy = f"""
#             select invoice_no,
#                    isnull(stamp_duty,0) sd,
#                    isnull(tl,0) tl,
#                    isnull(phcf,0) phcf
#             from PREMIUM_INVOICE
#             where invoice_no='{invoice_no}'
#             """
#             Levies = crud("R", sqlLevy)

#             premLevies = sum(
#                 float(levy.get("sd") or 0) +
#                 float(levy.get("tl") or 0) +
#                 float(levy.get("phcf") or 0)
#                 for levy in Levies
#             )

#             # Levied allocations for this receipt
#             sqLRctAllocation = f"""
#             select invoice_no,
#                    sum(isnull(allocated_amt,0)) as alloc_amt,
#                    sum(isnull(levied,0)) as levy_amt,
#                    (sum(isnull(allocated_amt,0))+sum(isnull(levied,0))) as T_allocated_amt
#             from premium_invoice_details_sammary
#             where allocated=1
#             and invoice_no='{invoice_no}'
#             and receipt_no='{receipt_no}'
#             group by invoice_no
#             """
#             leviedAmounts = crud("R", sqLRctAllocation)

#             alloc_amt_rec = t_allocate_rec = 0
#             for la in leviedAmounts:
#                 alloc_amt_rec = float(la.get("alloc_amt") or 0)
#                 t_allocate_rec = float(la.get("T_allocated_amt") or 0)

#             # Total levied deductions
#             sqlLevyDeductions = f"""
#             select sum(isnull(levied,0)) as levied
#             from premium_invoice_details_sammary
#             where allocated=1
#             and invoice_no='{invoice_no}'
#             """
#             leviedDeductions = crud("R", sqlLevyDeductions)

#             allLevy = sum(float(ld.get("levied") or 0) for ld in leviedDeductions)

#             levied = round(premLevies - allLevy, 2) if premLevies != allLevy else 0

#             if receipt_amount > levied:
#                 receipt_bal = receipt_amount - t_allocate_rec - levied
#                 unallocated_amt = net_premium - allocated_amt
#                 all_amt = min(receipt_bal, unallocated_amt)

#                 if all_amt > 0:
#                     all_amt = round(min(all_amt, net_premium), 2)

#                     # Insert allocation
#                     crud("U", f"""
#                     INSERT INTO premium_invoice_details_sammary
#                     (id_key, invoice_no, class, net_premium,
#                      allocated, allocated_amt, levied, receipt_no)
#                     values(
#                         (select max(id_key)+1 from premium_invoice_details_sammary),
#                         '{invoice_no}','{class_}',NULL,1,
#                         '{all_amt}','{levied}','{receipt_no}'
#                     )
#                     """)

#                     # Update receipt as commission paid
#                     crud("U", f"""
#                     update PREMIUM_RECEIPT
#                     set commis_paid='1'
#                     where invoice_no='{invoice_no}'
#                     and receipt_no='{receipt_no}'
#                     """)

#                     wh_log(f"{receipt_no} Allocated Successfully to {invoice_no}")

#     return HttpResponse("Allocation completed")

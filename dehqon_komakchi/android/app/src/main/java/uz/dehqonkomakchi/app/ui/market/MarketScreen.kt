package uz.dehqonkomakchi.app.ui.market

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.dehqonkomakchi.app.R
import uz.dehqonkomakchi.app.core.util.Regions
import uz.dehqonkomakchi.app.data.db.entity.ListingEntity
import java.time.LocalDate

@Composable
fun MarketScreen(viewModel: MarketViewModel = hiltViewModel()) {
    var tab by remember { mutableIntStateOf(0) }
    var showNewListing by remember { mutableStateOf(false) }
    var showNewGroup by remember { mutableStateOf(false) }
    var reportTargetId by remember { mutableStateOf<String?>(null) }

    val listings by viewModel.listings.collectAsState()
    val groups by viewModel.groups.collectAsState()

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(onClick = { if (tab == 0) showNewListing = true else showNewGroup = true }) {
                Icon(Icons.Filled.Add, contentDescription = stringResource(R.string.action_add))
            }
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            Text(stringResource(R.string.market_title), style = MaterialTheme.typography.headlineMedium, modifier = Modifier.padding(16.dp))
            TabRow(selectedTabIndex = tab) {
                Tab(selected = tab == 0, onClick = { tab = 0 }, text = { Text(stringResource(R.string.market_listings_tab)) })
                Tab(selected = tab == 1, onClick = { tab = 1 }, text = { Text(stringResource(R.string.market_groups_tab)) })
            }
            if (tab == 0) {
                if (listings.isEmpty()) {
                    Text(stringResource(R.string.market_empty), modifier = Modifier.padding(16.dp))
                } else {
                    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
                        items(listings, key = { it.id }) { listing ->
                            ListingCard(listing, onReport = { reportTargetId = listing.id })
                        }
                    }
                }
            } else {
                if (groups.isEmpty()) {
                    Text(stringResource(R.string.market_empty), modifier = Modifier.padding(16.dp))
                } else {
                    LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
                        items(groups, key = { it.id }) { group ->
                            Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                                Column(modifier = Modifier.padding(12.dp)) {
                                    Text(group.name, style = MaterialTheme.typography.titleMedium)
                                    Text(group.region, style = MaterialTheme.typography.bodyMedium)
                                    if (group.isAdmin) {
                                        Button(onClick = { }, modifier = Modifier.padding(top = 8.dp)) {
                                            Text(stringResource(R.string.group_send_offer))
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (showNewListing) {
        NewListingDialog(
            onDismiss = { showNewListing = false },
            onConfirm = { variety, qty, price, negotiable, region, contactMethod, contactValue, consent ->
                viewModel.createListing(
                    variety = variety, quantityKg = qty, priceSom = price, negotiable = negotiable,
                    region = region, photoPath = null, contactMethod = contactMethod,
                    contactValue = contactValue, contactConsent = consent, ownerName = "Foydalanuvchi",
                )
                showNewListing = false
            },
        )
    }

    if (showNewGroup) {
        NewGroupDialog(
            onDismiss = { showNewGroup = false },
            onConfirm = { name, region ->
                viewModel.createGroup(name, region, "Foydalanuvchi")
                showNewGroup = false
            },
        )
    }

    reportTargetId?.let { listingId ->
        ReportDialog(
            onDismiss = { reportTargetId = null },
            onConfirm = { reason ->
                viewModel.reportListing(listingId, reason, "")
                reportTargetId = null
            },
        )
    }
}

@Composable
private fun ListingCard(listing: ListingEntity, onReport: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(listing.variety, style = MaterialTheme.typography.titleMedium)
                IconButton(onClick = onReport) {
                    Icon(Icons.Filled.Flag, contentDescription = stringResource(R.string.cd_report_listing))
                }
            }
            Text("${listing.quantityKg} ${stringResource(R.string.unit_kg)}", style = MaterialTheme.typography.bodyMedium)
            Text(
                if (listing.negotiable) stringResource(R.string.market_listing_negotiable)
                else "${listing.priceSom ?: 0.0} ${stringResource(R.string.unit_som)}",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(listing.region, style = MaterialTheme.typography.bodyMedium)
            Text(LocalDate.ofEpochDay(listing.availabilityEpochDay).toString(), style = MaterialTheme.typography.bodyMedium)
            if (listing.contactConsent) {
                Text("${listing.contactMethod}: ${listing.contactValue}", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
private fun NewListingDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, Double, Double?, Boolean, String, String, String, Boolean) -> Unit,
) {
    var variety by remember { mutableStateOf("") }
    var quantity by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var negotiable by remember { mutableStateOf(false) }
    var region by remember { mutableStateOf(Regions.ALL.first()) }
    var contactMethod by remember { mutableStateOf("phone") }
    var contactValue by remember { mutableStateOf("") }
    var consent by remember { mutableStateOf(false) }
    var showConsentExplain by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.market_new_listing)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = variety, onValueChange = { variety = it }, label = { Text(stringResource(R.string.market_listing_variety)) }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = quantity, onValueChange = { quantity = it }, label = { Text(stringResource(R.string.market_listing_quantity)) }, modifier = Modifier.fillMaxWidth())
                Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Switch(checked = negotiable, onCheckedChange = { negotiable = it })
                    Text(stringResource(R.string.market_listing_negotiable), modifier = Modifier.padding(start = 8.dp))
                }
                if (!negotiable) {
                    OutlinedTextField(value = price, onValueChange = { price = it }, label = { Text(stringResource(R.string.market_listing_price)) }, modifier = Modifier.fillMaxWidth())
                }
                OutlinedTextField(value = region, onValueChange = { region = it }, label = { Text(stringResource(R.string.market_listing_region)) }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = contactValue, onValueChange = { contactValue = it }, label = { Text(stringResource(R.string.market_listing_contact)) }, modifier = Modifier.fillMaxWidth())
                Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Switch(checked = consent, onCheckedChange = { consent = it; if (it) showConsentExplain = true })
                    Text(stringResource(R.string.market_consent_title), modifier = Modifier.padding(start = 8.dp))
                }
                Text(stringResource(R.string.market_consent_body), style = MaterialTheme.typography.bodyMedium)
            }
        },
        confirmButton = {
            Button(onClick = {
                onConfirm(
                    variety, quantity.toDoubleOrNull() ?: 0.0,
                    if (negotiable) null else price.toDoubleOrNull(),
                    negotiable, region, contactMethod, contactValue, consent,
                )
            }) { Text(stringResource(R.string.action_save)) }
        },
        dismissButton = { Button(onClick = onDismiss) { Text(stringResource(R.string.action_cancel)) } },
    )
}

@Composable
private fun NewGroupDialog(onDismiss: () -> Unit, onConfirm: (String, String) -> Unit) {
    var name by remember { mutableStateOf("") }
    var region by remember { mutableStateOf(Regions.ALL.first()) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.group_create)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text(stringResource(R.string.group_name)) }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = region, onValueChange = { region = it }, label = { Text(stringResource(R.string.market_listing_region)) }, modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = { Button(onClick = { onConfirm(name, region) }) { Text(stringResource(R.string.action_save)) } },
        dismissButton = { Button(onClick = onDismiss) { Text(stringResource(R.string.action_cancel)) } },
    )
}

@Composable
private fun ReportDialog(onDismiss: () -> Unit, onConfirm: (String) -> Unit) {
    val reasons = listOf(
        "spam" to R.string.market_report_spam,
        "fraud" to R.string.market_report_fraud,
        "inappropriate" to R.string.market_report_inappropriate,
        "other" to R.string.market_report_other,
    )
    var selected by remember { mutableStateOf(reasons.first().first) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.market_report_reason_title)) },
        text = {
            Column {
                reasons.forEach { (key, labelRes) ->
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        RadioButton(selected = selected == key, onClick = { selected = key })
                        Text(stringResource(labelRes))
                    }
                }
            }
        },
        confirmButton = { Button(onClick = { onConfirm(selected) }) { Text(stringResource(R.string.action_send)) } },
        dismissButton = { Button(onClick = onDismiss) { Text(stringResource(R.string.action_cancel)) } },
    )
}
